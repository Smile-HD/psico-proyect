"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import Breadcrumb from "@/components/ui/Breadcrumb";
import Button from "@/components/ui/Button";
import { ErrorState, Notice } from "@/components/ui/Feedback";
import LikertMatrix, { type LikertItem } from "@/components/ui/LikertMatrix";
import Skeleton from "@/components/ui/Skeleton";
import { getToken, useSessionUser } from "@/lib/auth";
import {
	completeSession,
	getSession,
	mapSessionError,
	newIntentKey,
	saveSessionResponses,
	type SessionDetail,
	type SessionItem,
	type SessionResponseInput,
} from "@/lib/session-api";
import styles from "./page.module.css";

const SAVE_DELAY = 700;
type Answers = Record<string, string>;
type SaveIntent = { key: string; responses: SessionResponseInput[] };

function matrixItems(items: SessionItem[]): LikertItem[] {
	return items.map((item) => ({ id: item.id, order: item.item_order, text: item.text, required: item.required, options: item.response_options.map((option) => ({ id: option.id, order: option.display_order, label: option.label })) }));
}

function initialAnswers(detail: SessionDetail): Answers {
	return Object.fromEntries((detail.projection?.scales.flatMap((scale) => scale.items) ?? []).filter((item) => item.response_option_id).map((item) => [item.id, item.response_option_id as string]));
}

function responsePayload(answers: Answers): SessionResponseInput[] {
	return Object.entries(answers).map(([item_id, response_option_id]) => ({ item_id, response_option_id }));
}

function requiredMissing(items: SessionItem[], answers: Answers) { return items.filter((item) => item.required && !answers[item.id]); }

function focusItem(item: SessionItem | undefined) {
	if (!item) return;
	requestAnimationFrame(() => {
		const input = Array.from(document.querySelectorAll<HTMLInputElement>('input[type="radio"]')).find((candidate) => candidate.getAttribute("aria-label")?.startsWith(`${item.text}:`));
		input?.focus();
	});
}

export default function SessionPage() {
	const params = useParams<{ id: string }>();
	const router = useRouter();
	const { user, ready } = useSessionUser();
	const [session, setSession] = useState<SessionDetail | null>(null);
	const [answers, setAnswers] = useState<Answers>({});
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
	const headingRef = useRef<HTMLHeadingElement>(null);
	const focusedRef = useRef(false);
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
				setSession(data);
			})
			.catch(() => {
				if (!cancelled) setLoadError(true);
			});
		return () => {
			cancelled = true;
			if (timerRef.current) clearTimeout(timerRef.current);
		};
	}, [params.id, ready, reloadKey, router, user]);
	useEffect(() => {
		if (session && !focusedRef.current) {
			focusedRef.current = true;
			requestAnimationFrame(() => headingRef.current?.focus());
		}
	}, [session]);
	async function saveIntent(intent: SaveIntent) {
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
	async function drainQueue() {
		while (queueRef.current.length) {
			const next = queueRef.current.shift();
			if (!next || !(await saveIntent(next))) break;
		}
	}
	function ensureDrain() {
		if (!drainRef.current) {
			drainRef.current = drainQueue().finally(() => {
				drainRef.current = null;
			});
		}
		return drainRef.current;
	}
	function queueIntent(intent: SaveIntent) {
		queueRef.current.push(intent);
		void ensureDrain();
	}
	function flushPending() {
		if (timerRef.current) clearTimeout(timerRef.current);
		const pending = pendingRef.current;
		pendingRef.current = null;
		if (pending) queueRef.current.push(pending);
		return ensureDrain();
	}
	function changeAnswer(itemId: string, optionId: string) {
		const next = { ...answersRef.current, [itemId]: optionId };
		answersRef.current = next;
		setAnswers(next);
		setCompletionError("");
		setSaveStatus("idle");
		let intent = pendingRef.current;
		if (!intent) {
			intent = { key: newIntentKey(), responses: [] };
			pendingRef.current = intent;
		}
		intent.responses = responsePayload(next);
		if (timerRef.current) clearTimeout(timerRef.current);
		timerRef.current = setTimeout(() => {
			const readyIntent = pendingRef.current;
			pendingRef.current = null;
			if (readyIntent) queueIntent(readyIntent);
		}, SAVE_DELAY);
	}
	function retrySave() {
		const failed = failedRef.current;
		if (!failed) return;
		failedRef.current = null;
		queueRef.current.unshift(failed);
		void ensureDrain();
	}
	async function complete() {
		if (!session || completing) return;
		const items = session.projection?.scales.flatMap((scale) => scale.items) ?? [];
		const missing = requiredMissing(items, answersRef.current);
		if (missing.length) {
			setCompletionError("Responda los ítems marcados como obligatorios antes de completar.");
			focusItem(missing[0]);
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
			setSession((current) => (current ? { ...current, status: result.status } : current));
		} catch (error) {
			const mapped = mapSessionError(error);
			if (mapped.kind === "validation") completionKeyRef.current = null;
			setCompletionError(
				mapped.kind === "validation"
					? "Aún faltan respuestas obligatorias. Revise los ítems marcados."
					: mapped.message,
			);
			if (mapped.kind === "validation") focusItem(requiredMissing(items, answersRef.current)[0]);
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

	const projection = session.projection;
	const saveMessage =
		saveStatus === "saving"
			? "Guardando respuestas…"
			: saveStatus === "saved"
				? "Respuestas guardadas."
				: saveError;

	return (
		<div className={styles.page}>
			<Breadcrumb items={[{ label: "Evaluaciones", href: "/evaluacion" }, { label: "Sesión", current: true }]} />
			<header className={styles.header}>
				<p className={styles.eyebrow}>Evaluación</p>
				<h1 ref={headingRef} tabIndex={-1}>Completar evaluación</h1>
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
			) : (
				<>
					{projection.scales.map((scale) => (
						<section className={styles.scale} key={scale.id} aria-labelledby={`scale-${scale.id}`}>
							<h2 id={`scale-${scale.id}`}>{scale.label}</h2>
							<LikertMatrix
								caption={`${scale.label} — opciones de respuesta`}
								items={matrixItems(scale.items)}
								interactive
								valueByItem={answers}
								onChange={changeAnswer}
							/>
						</section>
					))}
					<footer className={styles.actions}>
						<p>Los ítems marcados como <strong>obligatorios</strong> deben tener una respuesta.</p>
						<Button type="button" busy={completing} pendingLabel="Completando…" onClick={complete}>Completar evaluación</Button>
					</footer>
				</>
			)}
		</div>
	);
}
