"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import Breadcrumb from "@/components/ui/Breadcrumb";
import Button from "@/components/ui/Button";
import { ErrorState, Notice } from "@/components/ui/Feedback";
import Skeleton from "@/components/ui/Skeleton";
import { getToken, useSessionUser } from "@/lib/auth";
import {
	clearActiveSessionId,
	completeSession,
	getActiveSessionId,
	getSession,
	mapSessionError,
	newIntentKey,
	saveSessionResponses,
	storeActiveSessionId,
	type SessionDetail,
	type SessionItem,
	type SessionResponseInput,
} from "@/lib/session-api";

import styles from "./page.module.css";

const SAVE_DELAY = 700;
type Answers = Record<string, string>;
type SaveIntent = { key: string; responses: SessionResponseInput[] };

function sessionItems(detail: SessionDetail): SessionItem[] {
	return (detail.projection?.scales ?? [])
		.slice()
		.sort((a, b) => a.display_order - b.display_order)
		.flatMap((scale) =>
			scale.items.slice().sort((a, b) => a.item_order - b.item_order),
		);
}

function initialAnswers(detail: SessionDetail): Answers {
	return Object.fromEntries(
		sessionItems(detail)
			.filter((item) => item.response_option_id)
			.map((item) => [item.id, item.response_option_id as string]),
	);
}

function requiredMissing(items: SessionItem[], answers: Answers): SessionItem[] {
	return items.filter((item) => item.required && !answers[item.id]);
}

export default function SessionPage() {
	const params = useParams<{ id: string }>();
	const router = useRouter();
	const { user, ready } = useSessionUser();
	const [session, setSession] = useState<SessionDetail | null>(null);
	const [answers, setAnswers] = useState<Answers>({});
	const [currentIndex, setCurrentIndex] = useState(0);
	const [loadError, setLoadError] = useState(false);
	const [reloadKey, setReloadKey] = useState(0);
	const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
	const [saveError, setSaveError] = useState("");
	const [completionError, setCompletionError] = useState("");
	const [completing, setCompleting] = useState(false);
	const answersRef = useRef<Answers>({});
	const pendingRef = useRef<SaveIntent | null>(null);
	const failedRef = useRef<SaveIntent | null>(null);
	const queueRef = useRef<SaveIntent[]>([]);
	const drainRef = useRef<Promise<void> | null>(null);
	const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const itemHeadingRef = useRef<HTMLHeadingElement>(null);
	const completionKeyRef = useRef<string | null>(null);

	useEffect(() => {
		if (!ready) return;
		if (!user) {
			router.replace("/login");
			return;
		}

		let cancelled = false;
		setSession(null);
		setLoadError(false);
		getSession(getToken() ?? "", params.id)
			.then((data) => {
				if (cancelled) return;
				const restored = initialAnswers(data);
				answersRef.current = restored;
				setAnswers(restored);
				const items = sessionItems(data);
				const firstUnanswered = items.findIndex((item) => !restored[item.id]);
				setCurrentIndex(firstUnanswered >= 0 ? firstUnanswered : 0);
				if (data.status === "completed") {
					if (getActiveSessionId() === params.id) clearActiveSessionId();
				} else {
					storeActiveSessionId(params.id);
				}
				setSession(data);
			})
			.catch((error) => {
				if (cancelled) return;
				const mapped = mapSessionError(error);
				if (
					(mapped.kind === "not_found" || mapped.kind === "forbidden") &&
					getActiveSessionId() === params.id
				) {
					clearActiveSessionId();
				}
				setLoadError(true);
			});
		return () => {
			cancelled = true;
			if (timerRef.current) clearTimeout(timerRef.current);
		};
	}, [params.id, ready, reloadKey, router, user]);

	useEffect(() => {
		if (!session || session.status === "completed") return;
		requestAnimationFrame(() => itemHeadingRef.current?.focus());
	}, [currentIndex, session]);

	async function saveIntent(intent: SaveIntent): Promise<boolean> {
		setSaveStatus("saving");
		try {
			await saveSessionResponses(getToken() ?? "", params.id, intent.responses, intent.key);
			failedRef.current = null;
			setSaveError("");
			setSaveStatus("saved");
			return true;
		} catch (error) {
			const mapped = mapSessionError(error);
			failedRef.current = intent;
			setSaveError(mapped.message);
			setSaveStatus("error");
			return false;
		}
	}

	async function drainQueue(): Promise<void> {
		while (queueRef.current.length) {
			const next = queueRef.current.shift();
			if (!next || !(await saveIntent(next))) break;
		}
	}

	function ensureDrain(): Promise<void> {
		if (!drainRef.current) {
			drainRef.current = drainQueue().finally(() => {
				drainRef.current = null;
			});
		}
		return drainRef.current;
	}

	function queueIntent(intent: SaveIntent): void {
		queueRef.current.push(intent);
		void ensureDrain();
	}

	function flushPending(): Promise<void> {
		if (timerRef.current) clearTimeout(timerRef.current);
		const pending = pendingRef.current;
		pendingRef.current = null;
		if (pending) queueRef.current.push(pending);
		return ensureDrain();
	}

	function changeAnswer(itemId: string, optionId: string): void {
		const next = { ...answersRef.current, [itemId]: optionId };
		answersRef.current = next;
		setAnswers(next);
		setCompletionError("");
		setSaveStatus("idle");
		const failed = failedRef.current;
		if (failed && failed.responses[0]?.item_id !== itemId) {
			failedRef.current = null;
			queueRef.current.unshift(failed);
			void ensureDrain();
		}

		let intent = pendingRef.current;
		if (intent && intent.responses[0]?.item_id !== itemId) {
			pendingRef.current = null;
			if (timerRef.current) clearTimeout(timerRef.current);
			queueIntent(intent);
			intent = null;
		}
		if (!intent) {
			intent = { key: newIntentKey(), responses: [] };
			pendingRef.current = intent;
		}
		intent.responses = [{ item_id: itemId, response_option_id: optionId }];
		if (timerRef.current) clearTimeout(timerRef.current);
		timerRef.current = setTimeout(() => {
			const readyIntent = pendingRef.current;
			pendingRef.current = null;
			if (readyIntent) queueIntent(readyIntent);
		}, SAVE_DELAY);
	}

	function retrySave(): void {
		const failed = failedRef.current;
		if (!failed) return;
		failedRef.current = null;
		queueRef.current.unshift(failed);
		void ensureDrain();
	}

	function moveToItem(index: number): void {
		setCurrentIndex(index);
		setCompletionError("");
	}

	async function complete(): Promise<void> {
		if (!session || completing) return;
		const items = sessionItems(session);
		const missing = requiredMissing(items, answersRef.current);
		if (missing.length) {
			setCompletionError("Responda los ítems marcados como obligatorios antes de completar.");
			const missingIndex = items.findIndex((item) => item.id === missing[0].id);
			if (missingIndex >= 0) setCurrentIndex(missingIndex);
			return;
		}

		setCompleting(true);
		setCompletionError("");
		await flushPending();
		if (failedRef.current) {
			setCompletionError("Guarde las respuestas pendientes antes de completar la evaluación.");
			setCompleting(false);
			return;
		}
		try {
			const completionKey = completionKeyRef.current ?? newIntentKey();
			completionKeyRef.current = completionKey;
			const result = await completeSession(getToken() ?? "", params.id, completionKey);
			completionKeyRef.current = null;
			if (getActiveSessionId() === params.id) clearActiveSessionId();
			setSession((current) => (current ? { ...current, status: result.status } : current));
		} catch (error) {
			const mapped = mapSessionError(error);
			if (mapped.kind === "validation") completionKeyRef.current = null;
			setCompletionError(
				mapped.kind === "validation"
					? "Aún faltan respuestas obligatorias. Revise el ítem marcado."
					: mapped.message,
			);
			if (mapped.kind === "validation") {
				const serverMissing = requiredMissing(items, answersRef.current);
				const missingIndex = items.findIndex((item) => item.id === serverMissing[0]?.id);
				if (missingIndex >= 0) setCurrentIndex(missingIndex);
			}
		} finally {
			setCompleting(false);
		}
	}

	if (!ready || !user || (!session && !loadError)) {
		return <Skeleton variant="block" label="Cargando la evaluación…" />;
	}
	if (loadError || !session?.projection) {
		return (
			<div className={styles.page}>
				<ErrorState
					title="No se pudo cargar la evaluación"
					message="La sesión no está disponible. Intente nuevamente o vuelva al listado."
					onRetry={() => setReloadKey((current) => current + 1)}
					backAction={<Link href="/evaluacion">Volver a evaluaciones</Link>}
				/>
			</div>
		);
	}

	const items = sessionItems(session);
	const currentItem = items[currentIndex];
	const answeredCount = Object.keys(answers).length;
	const isLastItem = currentIndex === items.length - 1;
	const saveMessage =
		saveStatus === "saving"
			? "Guardando respuesta…"
			: saveStatus === "saved"
				? "Respuesta guardada."
				: saveError;

	return (
		<div className={styles.page}>
			<Breadcrumb items={[{ label: "Evaluaciones", href: "/evaluacion" }, { label: "Sesión", current: true }]} />
			<header className={styles.header}>
				<p className={styles.eyebrow}>Evaluación</p>
				<h1>Completar evaluación</h1>
				<p className={styles.intro}>Seleccione una etiqueta por cada ítem. Sus respuestas se guardan automáticamente.</p>
			</header>

			{saveStatus !== "idle" ? (
				<div className={styles.feedback}>
					<Notice tone={saveStatus === "error" ? "warning" : saveStatus === "saved" ? "success" : "info"} role="status" message={saveMessage} />
					{saveStatus === "error" ? <Button type="button" variant="secondary" onClick={retrySave}>Reintentar guardado</Button> : null}
				</div>
			) : null}
			{completionError ? <Notice tone="error" role="alert" message={completionError} /> : null}

			{session.status === "completed" ? (
				<section className={styles.complete} aria-labelledby="completed-heading">
					<h2 id="completed-heading">Evaluación completada</h2>
					<p>Sus respuestas fueron registradas. Esta etapa no muestra puntuaciones ni resultados.</p>
				</section>
			) : currentItem ? (
				<>
					<section className={styles.progress} aria-label="Progreso de la evaluación">
						<p className={styles.progressLabel} aria-live="polite">
							Ítem {currentIndex + 1} de {items.length}
							<span> · {answeredCount} respondido{answeredCount === 1 ? "" : "s"}</span>
						</p>
						<div
							className={styles.progressBar}
							role="progressbar"
							aria-label="Avance de la evaluación"
							aria-valuenow={currentIndex + 1}
							aria-valuemin={1}
							aria-valuemax={items.length}
						>
							<span style={{ width: `${((currentIndex + 1) / items.length) * 100}%` }} />
						</div>
					</section>

					<section className={styles.itemCard} aria-labelledby={`item-${currentItem.id}`}>
						<h2 id={`item-${currentItem.id}`} ref={itemHeadingRef} tabIndex={-1} className={styles.itemHeading}>
							{currentItem.text}
							{currentItem.required ? <span className={styles.required}> (obligatorio)</span> : null}
						</h2>
						<fieldset className={styles.options} aria-required={currentItem.required || undefined}>
							<legend className={styles.visuallyHidden}>Seleccione una opción para este ítem</legend>
							{currentItem.response_options
								.slice()
								.sort((a, b) => a.display_order - b.display_order)
								.map((option) => {
									const selected = answers[currentItem.id] === option.id;
									return (
										<label className={styles.option} data-selected={selected} key={option.id}>
											<input
												className={styles.radio}
												type="radio"
												name={`item-${currentItem.id}`}
												value={option.id}
												checked={selected}
												aria-label={`${currentItem.text}: ${option.label}`}
												onChange={(event) => {
													if (event.target.checked) changeAnswer(currentItem.id, option.id);
												}}
											/>
											<span className={styles.optionMarker} aria-hidden="true" />
											<span>{option.label}</span>
										</label>
									);
								})}
						</fieldset>
						<p className={styles.requiredHint}>Los ítems marcados como <strong>obligatorios</strong> deben tener una respuesta.</p>
					</section>

					<nav className={styles.actions} aria-label="Navegación entre ítems">
						<Button type="button" variant="secondary" onClick={() => moveToItem(currentIndex - 1)} disabled={currentIndex === 0}>
							Anterior
						</Button>
						{isLastItem ? (
							<Button type="button" busy={completing} pendingLabel="Completando…" onClick={complete}>
								Completar evaluación
							</Button>
						) : (
							<Button type="button" onClick={() => moveToItem(currentIndex + 1)}>
								Siguiente
							</Button>
						)}
					</nav>
				</>
			) : (
				<Notice tone="warning" role="alert" message="Esta evaluación no contiene ítems disponibles." />
			)}
		</div>
	);
}
