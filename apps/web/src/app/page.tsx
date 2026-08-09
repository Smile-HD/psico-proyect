import { unstable_noStore as noStore } from "next/cache";

import { Notice } from "@/components/ui/Feedback";
import StatusLabel from "@/components/ui/StatusLabel";

import styles from "./page.module.css";

type SeedStatus = {
	seed: {
		items: number;
		reference_sets: number;
		profiles: number;
		sessions: number;
		responses: number;
		consent_grants: number;
	};
	manifest: {
		seed_version: string;
		checksum: string;
		executed_at: string | null;
	} | null;
};

async function fetchJson<T>(url: string): Promise<T> {
	const res = await fetch(url, { cache: "no-store" });
	if (!res.ok) {
		throw new Error(`HTTP ${res.status}`);
	}
	return (await res.json()) as T;
}

export default async function Home() {
	noStore();

	const apiBase = process.env.API_BASE_URL ?? "http://api:8000";
	const [health, seed] = await Promise.all([
		fetchJson<{ status?: string }>(`${apiBase}/health`),
		fetchJson<SeedStatus>(`${apiBase}/api/v1/seed/status`),
	]);
	const healthOk = health.status === "ok";

	return (
		<div className={styles.page}>
			<header className={styles.hero}>
				<p className={styles.eyebrow}>TestPsico · entorno de investigación</p>
				<h1>Estado del servicio</h1>
				<p className={styles.lead}>
					Información operativa del entorno sintético para comprobar la
					disponibilidad y el contenido de referencia.
				</p>
			</header>

			<section
				className={styles.statusSection}
				aria-labelledby="health-heading"
			>
				<div className={styles.sectionHeading}>
					<div>
						<p className={styles.kicker}>Disponibilidad</p>
						<h2 id="health-heading">Salud de la API</h2>
					</div>
					<StatusLabel
						kind={healthOk ? "success" : "warning"}
						symbol={healthOk ? "✓" : "!"}
					>
						{healthOk ? "Disponible" : "No disponible"}
					</StatusLabel>
				</div>
				{healthOk ? (
					<p className={styles.supportingText}>
						El servicio respondió correctamente al último control.
					</p>
				) : (
					<Notice
						tone="warning"
						role="alert"
						message="La API respondió con un estado no disponible. Revise el servicio y vuelva a intentar."
					/>
				)}
			</section>

			<section className={styles.seedSection} aria-labelledby="seed-heading">
				<div className={styles.sectionHeading}>
					<div>
						<p className={styles.kicker}>Contenido cargado</p>
						<h2 id="seed-heading">Semilla de referencia</h2>
					</div>
					<StatusLabel kind="reference" symbol="·">
						Datos sintéticos
					</StatusLabel>
				</div>
				<p className={styles.supportingText}>
					El contenido se utiliza únicamente para investigación y pruebas del
					sistema; no representa validación clínica.
				</p>
				<dl className={styles.summary}>
					<div>
						<dt>Ítems</dt>
						<dd>{seed.seed.items}</dd>
					</div>
					<div>
						<dt>Conjuntos de referencia</dt>
						<dd>{seed.seed.reference_sets}</dd>
					</div>
					<div>
						<dt>Perfiles</dt>
						<dd>{seed.seed.profiles}</dd>
					</div>
					<div>
						<dt>Sesiones</dt>
						<dd>{seed.seed.sessions}</dd>
					</div>
					<div>
						<dt>Respuestas</dt>
						<dd>{seed.seed.responses}</dd>
					</div>
					<div>
						<dt>Consentimientos</dt>
						<dd>{seed.seed.consent_grants}</dd>
					</div>
				</dl>
				{seed.manifest ? (
					<p className={styles.manifest}>
						Semilla {seed.manifest.seed_version} · ejecutada el{" "}
						{new Date(seed.manifest.executed_at ?? "").toLocaleString("es-ES")}
					</p>
				) : null}
			</section>
		</div>
	);
}
