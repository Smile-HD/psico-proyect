"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import Button from "@/components/ui/Button";
import { ErrorState, Notice } from "@/components/ui/Feedback";
import EmptyState from "@/components/ui/EmptyState";
import Skeleton from "@/components/ui/Skeleton";
import { getToken, useSessionUser } from "@/lib/auth";
import {
	createSession,
	getActiveSessionId,
	getSession,
	grantActiveConsent,
	listPublishedVersions,
	mapSessionError,
	newIntentKey,
	clearActiveSessionId,
	SessionApiError,
	storeActiveSessionId,
	type PublishedVersionSummary,
} from "@/lib/session-api";

import styles from "./page.module.css";

type StartNotice = { tone: "info" | "warning"; message: string };

const CONSENT_COPY =
	"Este entorno es de desarrollo. Todos los datos son sintéticos y marcados como research-only; no corresponden a personas reales ni a normas UAGRM. Al firmar, aceptás que tus respuestas sintéticas se usen para probar el sistema. Podés revocar el consentimiento en cualquier momento.";

export default function EvaluationPage() {
	const router = useRouter();
	const { user, ready } = useSessionUser();
	const [versions, setVersions] = useState<PublishedVersionSummary[] | null>(null);
	const [loadError, setLoadError] = useState(false);
	const [startNotice, setStartNotice] = useState<StartNotice | null>(null);
	const [startingId, setStartingId] = useState<string | null>(null);
	const [resumeSessionId, setResumeSessionId] = useState<string | null>(null);
	const [consentVersionId, setConsentVersionId] = useState<string | null>(null);
	const [consentError, setConsentError] = useState("");
	const [consentBusy, setConsentBusy] = useState(false);
	const [reloadKey, setReloadKey] = useState(0);

	useEffect(() => {
		if (!ready) return;
		if (!user) {
			router.replace("/login");
			return;
		}

		let cancelled = false;
		setVersions(null);
		setLoadError(false);
		setResumeSessionId(null);
		listPublishedVersions(getToken() ?? "")
			.then((result) => {
				if (!cancelled) setVersions(result.versions);
			})
			.catch(() => {
				if (!cancelled) setLoadError(true);
			});

		const storedSessionId = getActiveSessionId();
		if (storedSessionId) {
			getSession(getToken() ?? "", storedSessionId)
				.then((session) => {
					if (cancelled) return;
					if (session.status === "completed") {
						clearActiveSessionId();
						return;
					}
					setResumeSessionId(storedSessionId);
				})
				.catch((error) => {
					if (cancelled) return;
					const mapped = mapSessionError(error);
					if (mapped.kind === "not_found" || mapped.kind === "forbidden") {
						clearActiveSessionId();
						return;
					}
					setResumeSessionId(storedSessionId);
				});
		}
		return () => {
			cancelled = true;
		};
	}, [ready, reloadKey, router, user]);

	async function startEvaluation(versionId: string) {
		if (startingId) return;
		setStartingId(versionId);
		setStartNotice(null);
		try {
			const session = await createSession(
				getToken() ?? "",
				versionId,
				newIntentKey(),
			);
			storeActiveSessionId(session.id);
			router.push(`/evaluacion/sesiones/${session.id}`);
		} catch (error) {
			const mapped = mapSessionError(error);
			if (mapped.kind === "consent_required") {
				setConsentVersionId(versionId);
				setConsentError("");
				setStartNotice(null);
			} else {
				setStartNotice({
					tone: "info",
					message:
						error instanceof SessionApiError ? mapped.message : "No se pudo iniciar la evaluación.",
				});
			}
		} finally {
			setStartingId(null);
		}
	}

	async function acceptConsent(): Promise<void> {
		if (!consentVersionId || consentBusy) return;
		setConsentBusy(true);
		setConsentError("");
		try {
			await grantActiveConsent(getToken() ?? "", newIntentKey());
			const session = await createSession(getToken() ?? "", consentVersionId, newIntentKey());
			storeActiveSessionId(session.id);
			router.push(`/evaluacion/sesiones/${session.id}`);
		} catch (error) {
			setConsentError(mapSessionError(error).message);
		} finally {
			setConsentBusy(false);
		}
	}

	function cancelConsent(): void {
		if (consentBusy) return;
		setConsentVersionId(null);
		setConsentError("");
	}

	if (!ready || !user) {
		return <Skeleton variant="block" label="Cargando las evaluaciones…" />;
	}

	return (
		<div className={styles.page}>
			<header className={styles.header}>
				<div>
					<p className={styles.eyebrow}>Evaluación</p>
					<h1>Elegir evaluación</h1>
					<p className={styles.intro}>
						Seleccione una versión publicada para comenzar. Las opciones se muestran
						con sus etiquetas.
					</p>
				</div>
			</header>

			{resumeSessionId ? (
				<section className={styles.resumePanel} aria-labelledby="resume-heading">
					<div>
						<h2 id="resume-heading">Tiene una evaluación en curso</h2>
						<p>Puede continuar desde el último ítem guardado.</p>
					</div>
					<Link className={styles.resumeLink} href={`/evaluacion/sesiones/${resumeSessionId}`}>
						Continuar evaluación
					</Link>
				</section>
			) : null}

			{consentVersionId ? (
				<section className={styles.consentPanel} aria-labelledby="consent-heading">
					<div>
						<p className={styles.eyebrow}>Consentimiento informado</p>
						<h2 id="consent-heading">Antes de comenzar</h2>
					</div>
					<p>Para participar en esta evaluación necesitamos registrar su consentimiento.</p>
					<div className={styles.consentBody}>
						<strong>Consentimiento informado (investigación — datos sintéticos)</strong>
						<p>{CONSENT_COPY}</p>
					</div>
					{consentError ? <Notice tone="error" role="alert" message={consentError} /> : null}
					<div className={styles.consentActions}>
						<Button type="button" busy={consentBusy} pendingLabel="Registrando…" onClick={acceptConsent}>
							Aceptar y comenzar
						</Button>
						<Button type="button" variant="secondary" onClick={cancelConsent} disabled={consentBusy}>
							Cancelar
						</Button>
					</div>
				</section>
			) : null}

			{startNotice ? (
				<Notice tone={startNotice.tone} message={startNotice.message} />
			) : null}

			{loadError ? (
				<ErrorState
					title="No se pudieron cargar las evaluaciones"
					message="Revise el servicio e intente nuevamente."
					onRetry={() => setReloadKey((current) => current + 1)}
				/>
			) : versions === null ? (
				<Skeleton variant="block" label="Cargando las evaluaciones…" />
			) : versions.length === 0 ? (
				<EmptyState
					contextLabel="Evaluaciones disponibles"
					title="No hay evaluaciones disponibles"
					description="En este momento no hay versiones publicadas para iniciar."
				/>
			) : (
				<section aria-labelledby="available-heading">
					<h2 id="available-heading" className={styles.sectionHeading}>
						Versiones disponibles
					</h2>
					<ul className={styles.list}>
						{versions.map((version) => (
							<li className={styles.card} key={version.instrument_version_id}>
								<div>
									<p className={styles.key}>{version.instrument_key}</p>
									<h3>{version.title}</h3>
								</div>
								<Button
									type="button"
									busy={startingId === version.instrument_version_id}
									disabled={Boolean(startingId) && startingId !== version.instrument_version_id}
									pendingLabel="Iniciando…"
									onClick={() => startEvaluation(version.instrument_version_id)}
								>
									Comenzar evaluación
								</Button>
							</li>
						))}
					</ul>
				</section>
			)}
		</div>
	);
}
