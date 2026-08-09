"use client";

/**
 * /sesion — Evaluation wizard for the `evaluado` role.
 *
 * State machine:
 *   idle          – user arrives, test details loaded, no active session
 *   consenting    – showing consent agreement screen; user must accept
 *   starting      – POST /sessions in-flight
 *   resuming      – GET /sessions/{id}/resume in-flight (page reload)
 *   in_progress   – test running; ONE item per screen
 *   submitting    – POST /sessions/{id}/submit in-flight
 *   completed     – session finished
 *   error         – unrecoverable error
 *
 * Session ID is stored in sessionStorage so page reloads resume seamlessly.
 */

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import Button from "@/components/ui/Button";
import { ErrorState, Notice } from "@/components/ui/Feedback";
import { apiFetch, ApiError } from "@/lib/api";
import { getToken, useSessionUser } from "@/lib/auth";

import styles from "./page.module.css";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

// Seed instrument key — resolved dynamically to a real UUID at runtime via the API.
// Never used as a fallback UUID in POST /sessions.
const SEED_INSTRUMENT_KEY = "TP-S-01:v1";

const SESSION_STORAGE_KEY = "psico_active_session_id";

// ---------------------------------------------------------------------------
// Types matching API contracts
// ---------------------------------------------------------------------------

type ResponseOption = {
	id: string;
	display_order: number;
	label: string;
	locale: string;
};

type Item = {
	id: string;
	item_order: number;
	text: string;
	locale: string;
	required: boolean;
	response_options: ResponseOption[];
};

type Scale = {
	id: string;
	display_order: number;
	label: string;
	locale: string;
	items: Item[];
};

type PublishedVersion = {
	instrument_version_id: string;
	instrument_key: string;
	title: string;
	description: string | null;
	version_no: number;
	scales: Scale[];
};

type SavedResponse = {
	item_id: string;
	value: number;
};

type SessionCreateResponse = {
	id: string;
	status: string;
	instrument_version_id: string;
	started_at: string;
};

type SessionResumeResponse = {
	id: string;
	status: string;
	instrument_version_id: string;
	started_at: string;
	remaining_seconds: number | null;
	saved_responses: SavedResponse[];
};

type SubmitResponse = {
	id: string;
	status: string;
	completed_at: string;
	response_count: number;
};

type Phase =
	| "loading"
	| "idle"
	| "consenting"
	| "starting"
	| "resuming"
	| "in_progress"
	| "submitting"
	| "completed"
	| "error";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function flatItems(version: PublishedVersion): Item[] {
	return version.scales
		.slice()
		.sort((a, b) => a.display_order - b.display_order)
		.flatMap((s) =>
			s.items.slice().sort((a, b) => a.item_order - b.item_order),
		);
}

function optionValue(option: ResponseOption): number {
	return option.display_order;
}

function formatTime(seconds: number): string {
	const m = Math.floor(Math.max(0, seconds) / 60);
	const s = Math.floor(Math.max(0, seconds) % 60);
	return `${m}:${s.toString().padStart(2, "0")}`;
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function SesionPage() {
	const router = useRouter();
	const { user, ready } = useSessionUser();

	const [phase, setPhase] = useState<Phase>("loading");
	const [errorMsg, setErrorMsg] = useState<string | null>(null);

	const [version, setVersion] = useState<PublishedVersion | null>(null);
	const [items, setItems] = useState<Item[]>([]);
	const [sessionId, setSessionId] = useState<string | null>(null);
	const [responses, setResponses] = useState<Record<string, number>>({});
	const [responseCount, setResponseCount] = useState(0);

	const [consentError, setConsentError] = useState<string | null>(null);
	const [consentBusy, setConsentBusy] = useState(false);

	const [currentIndex, setCurrentIndex] = useState(0);
	const [remainingSeconds, setRemainingSeconds] = useState<number | null>(null);
	const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

	const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
	const savedKeys = useRef<Set<string>>(new Set());

	// ---------------------------------------------------------------------------
	// Auth Guard
	// ---------------------------------------------------------------------------

	useEffect(() => {
		if (!ready) return;
		if (!user) {
			router.replace("/login");
		}
	}, [ready, user, router]);

	// ---------------------------------------------------------------------------
	// Startup: Detect existing session or load published test
	// ---------------------------------------------------------------------------

	useEffect(() => {
		if (!ready || !user) return;

		const token = getToken() ?? "";
		const storedId =
			typeof window !== "undefined"
				? window.sessionStorage.getItem(SESSION_STORAGE_KEY)
				: null;

		if (storedId) {
			setPhase("resuming");
			resumeSession(storedId, token);
		} else {
			loadIdle(token);
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [ready, user]);

	// ---------------------------------------------------------------------------
	// Timer
	// ---------------------------------------------------------------------------

	function startTimer(initial: number | null) {
		if (timerRef.current) clearInterval(timerRef.current);
		if (initial === null) return;
		setRemainingSeconds(initial);
		timerRef.current = setInterval(() => {
			setRemainingSeconds((prev) => {
				if (prev === null) return null;
				if (prev <= 1) {
					clearInterval(timerRef.current!);
					return 0;
				}
				return prev - 1;
			});
		}, 1000);
	}

	useEffect(() => {
		return () => {
			if (timerRef.current) clearInterval(timerRef.current);
		};
	}, []);

	// ---------------------------------------------------------------------------
	// Load Idle State (Fetch published test version)
	// ---------------------------------------------------------------------------

	async function loadIdle(token: string) {
		if (!token) {
			console.warn("[Auth Warning] No JWT token found when loading test.");
		}
		try {
			let ver: PublishedVersion | null = null;

			// Primary: fetch by key — backend resolves "TP-S-01:v1" → real UUID.
			try {
				ver = await apiFetch<PublishedVersion>(
					`/api/v1/catalog/published-versions/${SEED_INSTRUMENT_KEY}`,
					{ token },
				);
				console.info(
					`[LoadIdle] Loaded version ${ver.instrument_version_id} via key lookup`,
				);
			} catch (keyErr) {
				// Key lookup failed — log and fall through to list-based fallback.
				if (keyErr instanceof ApiError) {
					console.warn(
						`[LoadIdle] Key lookup failed (${keyErr.payload.code}): ${keyErr.payload.message}. Trying list fallback…`,
					);
				} else {
					console.warn("[LoadIdle] Key lookup failed (network):", keyErr);
				}
			}

			// Fallback: fetch the list of published versions and pick the first.
			// This covers any key-resolution issue without hardcoding a UUID.
			if (!ver) {
				const list = await apiFetch<{ items: PublishedVersion[] } | PublishedVersion[]>(
					"/api/v1/catalog/published-versions",
					{ token },
				);
				const firstVer = Array.isArray(list) ? list[0] : (list as { items: PublishedVersion[] }).items?.[0];
				if (!firstVer) {
					throw new Error(
						"No hay versiones publicadas en la base de datos. Ejecute el seed primero.",
					);
				}
				ver = firstVer;
				console.info(
					`[LoadIdle] Loaded version ${ver.instrument_version_id} via list fallback`,
				);
			}

			setVersion(ver);
			setItems(flatItems(ver));
			setPhase("idle");
		} catch (err) {
			if (err instanceof ApiError) {
				console.error(
					`[LoadIdle Error] ${err.payload.code}: ${err.payload.message}`,
				);
			} else {
				console.error("[LoadIdle Error]", err);
			}
			handleError(
				err,
				"No se pudo cargar la información del test. Verifique que los datos semilla estén cargados.",
			);
		}
	}

	// ---------------------------------------------------------------------------
	// Resume Session
	// ---------------------------------------------------------------------------

	async function resumeSession(sid: string, token: string) {
		try {
			const resume = await apiFetch<SessionResumeResponse>(
				`/api/v1/sessions/${sid}/resume`,
				{ token },
			);

			if (resume.status === "completed") {
				setPhase("completed");
				setResponseCount(resume.saved_responses.length);
				if (typeof window !== "undefined") {
					window.sessionStorage.removeItem(SESSION_STORAGE_KEY);
				}
				return;
			}

			setSessionId(resume.id);
			const restoredResponses: Record<string, number> = {};
			for (const r of resume.saved_responses) {
				restoredResponses[r.item_id] = r.value;
				savedKeys.current.add(`${resume.id}:${r.item_id}:${r.value}`);
			}
			setResponses(restoredResponses);

			const ver = await apiFetch<PublishedVersion>(
				`/api/v1/catalog/published-versions/${resume.instrument_version_id}`,
				{ token },
			);
			setVersion(ver);
			const flat = flatItems(ver);
			setItems(flat);

			const firstUnanswered = flat.findIndex((item) => !(item.id in restoredResponses));
			setCurrentIndex(firstUnanswered >= 0 ? firstUnanswered : flat.length - 1);

			startTimer(resume.remaining_seconds);
			setPhase("in_progress");
		} catch (err) {
			// Session not found in DB (stale sessionStorage from a previous DB state)
			// — clear it and fall back to loading a fresh idle state.
			console.warn(
				"[Session Warning] La sesión previa ya no existe o caducó. Creando una nueva.",
			);
			if (typeof window !== "undefined") {
				window.sessionStorage.removeItem(SESSION_STORAGE_KEY);
			}
			setSessionId(null);
			loadIdle(token);
		}
	}
	// ---------------------------------------------------------------------------
	// Inline Consent Agreement
	// ---------------------------------------------------------------------------

	async function handleGrantConsent() {
		const token = getToken() ?? "";
		setConsentBusy(true);
		setConsentError(null);
		try {
			// 1. Obtener las versiones de consentimiento desde la API
			const res = await apiFetch<unknown>("/api/v1/consent/versions", { token });
			const versionsList: Array<{ id: string; is_active: boolean }> = Array.isArray(res)
				? (res as Array<{ id: string; is_active: boolean }>)
				: (res as { versions?: Array<{ id: string; is_active: boolean }> })?.versions ?? [];

			// 2. Buscar la versión activa
			const activeConsent =
				versionsList.find((v) => v.is_active) ?? versionsList[0] ?? null;

			if (!activeConsent?.id) {
				console.error(
					"[Consent Error] No active consent version found. versions list:",
					versionsList,
				);
				throw new Error(
					"No se encontró una versión de consentimiento activa en la base de datos.",
				);
			}

			console.info(`[Consent] Granting consent version id=${activeConsent.id}`);

			// 3. Registrar el consentimiento dinámicamente
			await apiFetch<unknown>(`/api/v1/consent/${activeConsent.id}/grant`, {
				method: "POST",
				token,
			});

			// 4. Iniciar la sesión
			await startSession();
		} catch (err) {
			console.error("[Consent Grant Error]", err);
			const msg = err instanceof ApiError ? `${err.payload.code}: ${err.payload.message}` : String(err);
			setConsentError(`Error técnico: ${msg}`);
		} finally {
			setConsentBusy(false);
		}
	}
	// Start Session
	// ---------------------------------------------------------------------------

	async function handleStart() {
		setPhase("starting");
		try {
			await startSession();
		} catch (err) {
			if (err instanceof ApiError && err.payload.code === "CONFLICT") {
				setPhase("consenting");
			} else {
				handleError(err, "No se pudo iniciar la sesión.");
			}
		}
	}

	async function startSession() {
		const token = getToken() ?? "";
		// version MUST be loaded by loadIdle() before reaching this point.
		if (!version) {
			throw new Error(
				"No se pudo obtener la versión del test. Recargue la página e intente nuevamente.",
			);
		}
		const versionId = version.instrument_version_id;

		// 1. Create session — backend locks in the exact instrument_version_id
		const sess = await apiFetch<SessionCreateResponse>("/api/v1/sessions", {
			method: "POST",
			token,
			body: { instrument_version_id: versionId },
		});

		if (!sess || !sess.id) {
			throw new Error("El servidor no devolvió un ID de sesión válido.");
		}

		const newSessionId = sess.id;
		// The version UUID the backend actually locked (canonical source of truth)
		const lockedVersionId = sess.instrument_version_id;

		// 2. Persist session ID immediately so autosave can use it even before
		//    React state propagates
		if (typeof window !== "undefined") {
			window.sessionStorage.setItem(SESSION_STORAGE_KEY, newSessionId);
		}

		// 3. ALWAYS reload the version from the backend using the SESSION's locked
		//    instrument_version_id. Guarantees UI items ≡ session.instrument_version_id.
		const ver = await apiFetch<PublishedVersion>(
			`/api/v1/catalog/published-versions/${lockedVersionId}`,
			{ token },
		);
		setVersion(ver);
		const flatItemsList = flatItems(ver);
		setItems(flatItemsList);

		// 4. Update all React state atomically
		setSessionId(newSessionId);
		setCurrentIndex(0);
		setResponses({});
		savedKeys.current.clear();
		startTimer(null);
		setPhase("in_progress");
	}

	// ---------------------------------------------------------------------------
	// Select Likert Option → Autosave with Idempotency-Key
	// ---------------------------------------------------------------------------

	const handleSelectOption = useCallback(
		async (item: Item, option: ResponseOption) => {
			const activeSessionId =
				sessionId ||
				(typeof window !== "undefined"
					? window.sessionStorage.getItem(SESSION_STORAGE_KEY)
					: null);
			if (!activeSessionId) {
				console.error("[Session Error] Cannot save response: No active session ID");
				return;
			}

			const value = optionValue(option);
			const idempotencyKey = `${activeSessionId}:${item.id}:${value}`;

			setResponses((prev) => ({ ...prev, [item.id]: value }));

			if (savedKeys.current.has(idempotencyKey)) {
				return;
			}

			setSaveState("saving");
			const token = getToken() ?? "";
			try {
				await apiFetch<unknown>(`/api/v1/sessions/${activeSessionId}/responses`, {
					method: "POST",
					token,
					idempotencyKey,
					body: { item_id: item.id, value },
				});
				savedKeys.current.add(idempotencyKey);
				setSaveState("saved");
				setTimeout(() => setSaveState("idle"), 1800);
			} catch (err) {
				const payload = { item_id: item.id, value };
				if (err instanceof ApiError) {
					console.error(
						`[Session Error] POST /api/v1/sessions/${activeSessionId}/responses FAILED`,
						{
							code: err.payload.code,
							message: err.payload.message,
							sentPayload: payload,
							idempotencyKey,
						},
					);
					// 404 session_not_found: clear stale session and restart cleanly
					if (
						err.payload.code === "session_not_found" ||
						err.payload.code === "NOT_FOUND" ||
						err.payload.code === "HTTP_404"
					) {
						console.warn("[Session Error] Stale session ID detected — clearing and reloading.");
						if (typeof window !== "undefined") {
							window.sessionStorage.removeItem(SESSION_STORAGE_KEY);
						}
						setSessionId(null);
						setPhase("loading");
						loadIdle(token);
						return;
					}
				} else {
					console.error(
						`[Session Error] POST /api/v1/sessions/${activeSessionId}/responses FAILED (network)`,
						{ sentPayload: payload, err },
					);
				}
				setSaveState("error");
				setTimeout(() => setSaveState("idle"), 3000);
			}
		},
		[sessionId],
	);

	// ---------------------------------------------------------------------------
	// Navigation
	// ---------------------------------------------------------------------------

	function goNext() {
		setCurrentIndex((i) => Math.min(i + 1, items.length - 1));
		setSaveState("idle");
	}

	function goPrev() {
		setCurrentIndex((i) => Math.max(i - 1, 0));
		setSaveState("idle");
	}

	// ---------------------------------------------------------------------------
	// Submit
	// ---------------------------------------------------------------------------

	async function handleSubmit() {
		const activeSessionId =
			sessionId ||
			(typeof window !== "undefined"
				? window.sessionStorage.getItem(SESSION_STORAGE_KEY)
				: null);
		if (!activeSessionId) {
			console.error("[Session Error] Cannot submit session: No active session ID");
			handleError(
				new Error("no_session_id"),
				"No hay una sesión activa para enviar.",
			);
			return;
		}

		setPhase("submitting");
		const token = getToken() ?? "";
		try {
			const result = await apiFetch<SubmitResponse>(
				`/api/v1/sessions/${activeSessionId}/submit`,
				{ method: "POST", token },
			);
			setResponseCount(result.response_count);
			if (typeof window !== "undefined") {
				window.sessionStorage.removeItem(SESSION_STORAGE_KEY);
			}
			setPhase("completed");
		} catch (err) {
			handleError(err, "No se pudo enviar el test. Intente nuevamente.");
		}
	}

	// ---------------------------------------------------------------------------
	// Error Handling
	// ---------------------------------------------------------------------------

	function handleError(err: unknown, fallback: string) {
		if (
			err instanceof ApiError &&
			["UNAUTHORIZED", "FORBIDDEN", "insufficient_role"].includes(err.payload.code)
		) {
			console.warn(`[Auth Error] ${err.payload.code}: ${err.payload.message}`);
		} else {
			console.error("[Session Error]", err);
		}
		const msg =
			err instanceof ApiError
				? `${fallback} (${err.payload.message})`
				: fallback;
		setErrorMsg(msg);
		setPhase("error");
	}

	function handleRetry() {
		setPhase("loading");
		setErrorMsg(null);
		const token = getToken() ?? "";
		loadIdle(token);
	}

	// ---------------------------------------------------------------------------
	// Derived Values
	// ---------------------------------------------------------------------------

	const totalItems = items.length;
	const answeredCount = Object.keys(responses).length;
	const progressPct = totalItems > 0 ? (answeredCount / totalItems) * 100 : 0;
	const currentItem = items[currentIndex] ?? null;
	const currentValue = currentItem ? responses[currentItem.id] ?? null : null;
	const isLastItem = currentIndex === items.length - 1;
	const allAnswered = answeredCount === totalItems && totalItems > 0;
	const isTimerUrgent =
		remainingSeconds !== null && remainingSeconds > 0 && remainingSeconds <= 60;

	// ---------------------------------------------------------------------------
	// Render
	// ---------------------------------------------------------------------------

	if (!ready) return null;

	if (phase === "error") {
		return (
			<div className={styles.page}>
				<ErrorState
					title="Algo salió mal"
					message={errorMsg ?? "Error desconocido."}
					onRetry={handleRetry}
				/>
			</div>
		);
	}

	if (
		phase === "loading" ||
		phase === "starting" ||
		phase === "resuming" ||
		phase === "submitting"
	) {
		const label = {
			loading: "Cargando…",
			starting: "Iniciando sesión…",
			resuming: "Retomando sesión…",
			submitting: "Enviando respuestas…",
		}[phase];
		return (
			<div className={styles.page}>
				<div className={styles.loading} role="status" aria-live="polite">
					{label}
				</div>
			</div>
		);
	}

	if (phase === "completed") {
		return (
			<div className={styles.page}>
				<div className={styles.completedPanel} role="main">
					<div className={styles.completedIcon} aria-hidden="true">
						✅
					</div>
					<h1 className={styles.completedTitle}>¡Test completado!</h1>
					<p className={styles.completedMeta}>
						Registraste <strong>{responseCount}</strong> respuesta
						{responseCount === 1 ? "" : "s"}.
					</p>
					<p className={styles.completedMeta}>
						Los resultados estarán disponibles una vez que el sistema los procese.
					</p>
					<p style={{ color: "var(--color-ink-2)", fontSize: "var(--font-size-supporting)" }}>
						Todos los datos son sintéticos y de uso exclusivo para investigación.
					</p>
				</div>
			</div>
		);
	}

	if (phase === "consenting") {
		return (
			<div className={styles.page}>
				<div className={styles.startPanel}>
					<p className={styles.eyebrow}>Consentimiento informado</p>
					<h1>Antes de comenzar</h1>
					<p className={styles.lead}>
						Para participar en este test necesitamos tu consentimiento.
					</p>
					<div className={styles.consentBody}>
						{`Consentimiento informado (investigación — datos sintéticos)\n\nEste entorno es de desarrollo. Todos los datos son sintéticos y marcados como research-only; no corresponden a personas reales ni a normas UAGRM. Al aceptar, consentís que tus respuestas sintéticas se usen para probar el sistema. Podés revocar el consentimiento en cualquier momento.`}
					</div>
					{consentError ? (
						<Notice tone="error" role="alert" message={consentError} />
					) : null}
					<div className={styles.startActions}>
						<Button
							type="button"
							variant="primary"
							busy={consentBusy}
							pendingLabel="Registrando…"
							onClick={handleGrantConsent}
						>
							Acepto y quiero comenzar
						</Button>
						<Button
							type="button"
							variant="secondary"
							onClick={() => setPhase("idle")}
							disabled={consentBusy}
						>
							Cancelar
						</Button>
					</div>
				</div>
			</div>
		);
	}

	if (phase === "idle") {
		return (
			<div className={styles.page}>
				<div className={styles.startPanel}>
					<p className={styles.eyebrow}>Evaluación psicotécnica</p>
					<h1>{version?.title ?? "Test Psicotécnico Sintético TP-S-01"}</h1>
					<p className={styles.lead}>
						{version?.description ??
							"Responde las preguntas del test para conocer tus áreas de interés. Podés pausar y retomar en cualquier momento."}
					</p>
					{totalItems > 0 ? (
						<p style={{ color: "var(--color-ink-2)", fontSize: "var(--font-size-supporting)" }}>
							{totalItems} ítems · Escala de respuesta Likert 1–5
						</p>
					) : null}
					<div className={styles.startActions}>
						<Button type="button" variant="primary" onClick={handleStart}>
							Iniciar test
						</Button>
					</div>
					<p style={{ color: "var(--color-ink-2)", fontSize: "var(--font-size-caption)" }}>
						Datos sintéticos · solo para investigación
					</p>
				</div>
			</div>
		);
	}

	if (phase === "in_progress" && currentItem) {
		return (
			<div className={styles.page}>
				{/* Progress Header */}
				<section aria-label="Progreso del test">
					<div className={styles.progressHeader}>
						<span className={styles.progressLabel}>
							Ítem {currentIndex + 1} de {totalItems} · {answeredCount} respondido
							{answeredCount === 1 ? "" : "s"}
						</span>
						{remainingSeconds !== null ? (
							<span
								className={styles.timerLabel}
								data-urgent={isTimerUrgent}
								aria-live="polite"
								aria-label={`Tiempo restante: ${formatTime(remainingSeconds)}`}
							>
								⏱ {formatTime(remainingSeconds)}
							</span>
						) : null}
					</div>
					<div className={styles.progressBar} role="progressbar" aria-valuenow={answeredCount} aria-valuemin={0} aria-valuemax={totalItems}>
						<div
							className={styles.progressFill}
							style={{ width: `${progressPct}%` }}
						/>
					</div>
				</section>

				{/* Item Card */}
				<article className={styles.itemCard} aria-labelledby="item-text">
					<div className={styles.itemHeader}>
						<span className={styles.itemOrder} aria-hidden="true">
							{currentIndex + 1}
						</span>
						<p id="item-text" className={styles.itemText}>
							{currentItem.text}
						</p>
					</div>

					{/* Likert Options */}
					<fieldset style={{ border: "none", margin: 0, padding: 0 }}>
						<legend className="sr-only">
							Selecciona una opción para: {currentItem.text}
						</legend>
						<ul className={styles.optionList} role="list">
							{currentItem.response_options
								.slice()
								.sort((a, b) => a.display_order - b.display_order)
								.map((option) => {
									const isSelected = currentValue === optionValue(option);
									return (
										<li key={option.id}>
											<label
												className={styles.optionLabel}
												data-selected={isSelected}
											>
												<input
													className={styles.optionRadio}
													type="radio"
													name={`item-${currentItem.id}`}
													value={String(optionValue(option))}
													checked={isSelected}
													aria-label={`${option.label} (${optionValue(option)} de 5)`}
													onChange={() => handleSelectOption(currentItem, option)}
												/>
												<span className={styles.optionDot} aria-hidden="true" />
												<span className={styles.optionText}>
													<strong>{optionValue(option)}.</strong>{" "}
													{option.label}
												</span>
											</label>
										</li>
									);
								})}
						</ul>
					</fieldset>

					{/* Save Status */}
					<p
						className={styles.saveStatus}
						data-state={saveState}
						aria-live="polite"
						aria-atomic="true"
					>
						{saveState === "saving" ? "Guardando…" : null}
						{saveState === "saved" ? "✓ Guardado" : null}
						{saveState === "error"
							? "No se pudo guardar. Compruebe su conexión."
							: null}
					</p>
				</article>

				{/* Item Navigation */}
				<nav className={styles.itemNav} aria-label="Navegación entre ítems">
					<Button
						type="button"
						variant="secondary"
						onClick={goPrev}
						disabled={currentIndex === 0}
					>
						← Anterior
					</Button>

					{!isLastItem ? (
						<Button
							type="button"
							variant="primary"
							onClick={goNext}
						>
							Siguiente →
						</Button>
					) : (
						<Button
							id="btn-submit"
							type="button"
							variant="primary"
							disabled={!allAnswered}
							onClick={handleSubmit}
							aria-disabled={!allAnswered}
						>
							{allAnswered
								? "Enviar test"
								: `Faltan ${totalItems - answeredCount} respuesta${totalItems - answeredCount === 1 ? "" : "s"}`}
						</Button>
					)}
				</nav>

				{/* Quick-Jump Summary Grid */}
				{totalItems <= 30 ? (
					<nav aria-label="Acceso rápido a ítems">
						<p style={{ fontSize: "var(--font-size-caption)", color: "var(--color-ink-2)", marginBottom: "var(--space-2)" }}>
							Acceso rápido
						</p>
						<div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-1)" }}>
							{items.map((item, idx) => {
								const answered = item.id in responses;
								const isCurrent = idx === currentIndex;
								return (
									<button
										key={item.id}
										type="button"
										aria-label={`Ir al ítem ${idx + 1}${answered ? " (respondido)" : ""}`}
										aria-current={isCurrent ? "true" : undefined}
										onClick={() => setCurrentIndex(idx)}
										style={{
											width: "2rem",
											height: "2rem",
											borderRadius: "var(--radius-sm)",
											border: isCurrent
												? "2px solid var(--color-accent)"
												: "1px solid var(--color-border)",
											background: answered
												? isCurrent
													? "var(--color-accent)"
													: "color-mix(in srgb, var(--color-accent) 15%, transparent)"
												: "var(--color-surface)",
											color: isCurrent && answered ? "var(--color-on-accent)" : "var(--color-ink-1)",
											cursor: "pointer",
											fontWeight: isCurrent ? "700" : "400",
											fontSize: "var(--font-size-caption)",
											transition: "background var(--motion-fast) var(--ease-standard)",
										}}
									>
										{idx + 1}
									</button>
								);
							})}
						</div>
					</nav>
				) : null}
			</div>
		);
	}

	return null;
}
