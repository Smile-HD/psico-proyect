"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { ErrorState } from "@/components/ui/Feedback";
import LikertMatrix, { type LikertItem } from "@/components/ui/LikertMatrix";
import Skeleton from "@/components/ui/Skeleton";
import StatusLabel from "@/components/ui/StatusLabel";
import styles from "./page.module.css";

type PublishedOption = {
	id: string;
	display_order: number;
	label: string;
	locale: string;
};

type PublishedItem = {
	id: string;
	item_order: number;
	text: string;
	locale: string;
	required: boolean;
	response_options: PublishedOption[];
};

type PublishedScale = {
	id: string;
	display_order: number;
	label: string;
	locale: string;
	items: PublishedItem[];
};

type PublishedVersion = {
	instrument_version_id: string;
	instrument_key: string;
	title: string;
	description: string | null;
	version_no: number;
	status: string;
	published_at: string | null;
	scales: PublishedScale[];
};

function toMatrixItems(items: PublishedItem[]): LikertItem[] {
	return items.map((item) => ({
		id: item.id,
		order: item.item_order,
		text: item.text,
		required: item.required,
		options: item.response_options.map((option) => ({
			id: option.id,
			order: option.display_order,
			label: option.label,
		})),
	}));
}

export default function PublishedViewPage() {
	const params = useParams<{ instrumentId: string; versionId: string }>();
	const [version, setVersion] = useState<PublishedVersion | null>(null);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		let cancelled = false;
		apiFetch<PublishedVersion>(
			`/api/v1/catalog/published-versions/${params.versionId}`,
			{
				token: localStorage.getItem("psico_token") ?? "",
			},
		)
			.then((data) => {
				if (!cancelled) setVersion(data);
			})
			.catch((err) => {
				if (!cancelled) {
					setError(
						err instanceof ApiError
							? err.payload.message
							: "No se pudo cargar la versión publicada.",
					);
				}
			});
		return () => {
			cancelled = true;
		};
	}, [params.versionId]);

	if (error) {
		return (
			<main id="main-content" className={styles.root}>
				<ErrorState
					title="No se pudo cargar la versión publicada"
					message={error}
					backAction={
						<Link href="/catalogo" className={styles.footerLink}>
							Volver al catálogo
						</Link>
					}
				/>
			</main>
		);
	}

	if (!version) {
		return (
			<main id="main-content" className={styles.root}>
				<Skeleton variant="heading" />
				<Skeleton variant="table" />
			</main>
		);
	}

	return (
		<main id="main-content" className={styles.root}>
			<header className={styles.header}>
				<h1>{version.title}</h1>
				<p className={styles.metadata}>
					{version.instrument_key} · v{version.version_no} ·{" "}
					<StatusLabel kind="published">Publicada</StatusLabel>
					{version.published_at
						? ` · ${new Date(version.published_at).toLocaleString("es-ES")}`
						: null}
				</p>
				{version.description ? (
					<p className={styles.description}>{version.description}</p>
				) : null}
			</header>

			<p className={styles.disclaimer}>
				Esta es una vista exploratoria de orientación. Las opciones se presentan
				con sus etiquetas; los valores numéricos internos no se muestran.
			</p>

			{version.scales.map((scale) => (
				<section key={scale.id} className={styles.scale} aria-labelledby={`scale-${scale.id}`}>
					<h2 id={`scale-${scale.id}`}>
						{scale.display_order}. {scale.label}
					</h2>
					<LikertMatrix
						caption={`${scale.label} — opciones de respuesta`}
						items={toMatrixItems(scale.items)}
					/>
				</section>
			))}

			<footer className={styles.footer}>
				<Link
					className={styles.footerLink}
					href={`/catalogo/${params.instrumentId}/versiones/${params.versionId}`}
				>
					Volver al detalle
				</Link>
				<p className={styles.footerNote}>
					Contenido sintético y de uso exclusivo para investigación
					(research-only).
				</p>
			</footer>
		</main>
	);
}
