"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import Button from "@/components/ui/Button";
import { ErrorState, Notice } from "@/components/ui/Feedback";
import EmptyState from "@/components/ui/EmptyState";
import Skeleton from "@/components/ui/Skeleton";
import { getToken, useSessionUser } from "@/lib/auth";
import {
	createSession,
	listPublishedVersions,
	mapSessionError,
	newIntentKey,
	SessionApiError,
	type PublishedVersionSummary,
} from "@/lib/session-api";

import styles from "./page.module.css";

type StartNotice = { tone: "info" | "warning"; message: string };

export default function EvaluationPage() {
	const router = useRouter();
	const { user, ready } = useSessionUser();
	const [versions, setVersions] = useState<PublishedVersionSummary[] | null>(null);
	const [loadError, setLoadError] = useState(false);
	const [startNotice, setStartNotice] = useState<StartNotice | null>(null);
	const [startingId, setStartingId] = useState<string | null>(null);
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
		listPublishedVersions(getToken() ?? "")
			.then((result) => {
				if (!cancelled) setVersions(result.versions);
			})
			.catch(() => {
				if (!cancelled) setLoadError(true);
			});
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
			router.push(`/evaluacion/sesiones/${session.id}`);
		} catch (error) {
			const mapped = mapSessionError(error);
			setStartNotice({
				tone: mapped.kind === "consent_required" ? "warning" : "info",
				message:
					error instanceof SessionApiError ? mapped.message : "No se pudo iniciar la evaluación.",
			});
		} finally {
			setStartingId(null);
		}
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
