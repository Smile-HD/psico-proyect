"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { getSessionUser } from "@/lib/auth";

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
			<main
				style={{
					fontFamily: "system-ui, sans-serif",
					maxWidth: 720,
					margin: "2rem auto",
					padding: "0 1rem",
				}}
			>
				<h1>Vista del evaluado</h1>
				<p style={{ color: "#b3261e" }}>{error}</p>
				<Link href="/catalogo">← Volver al catálogo</Link>
			</main>
		);
	}

	if (!version) {
		return (
			<p style={{ fontFamily: "system-ui, sans-serif", padding: "2rem" }}>
				Cargando…
			</p>
		);
	}

	return (
		<main
			style={{
				fontFamily: "system-ui, sans-serif",
				maxWidth: 760,
				margin: "2rem auto",
				padding: "0 1rem",
			}}
		>
			<header>
				<h1 style={{ marginBottom: "0.25rem" }}>{version.title}</h1>
				<p style={{ margin: 0, color: "#666" }}>
					{version.instrument_key} · v{version.version_no} · publicada el{" "}
					{version.published_at
						? new Date(version.published_at).toLocaleString("es-ES")
						: ""}
				</p>
				{version.description ? <p>{version.description}</p> : null}
			</header>

			<p style={{ color: "#666", fontSize: "0.9rem" }}>
				Esta es una vista exploratoria de orientación. Las opciones se presentan
				con sus etiquetas; los valores numéricos internos no se muestran.
			</p>

			{version.scales.map((scale) => (
				<section key={scale.id} style={{ marginTop: "1.5rem" }}>
					<h2>
						{scale.display_order}. {scale.label}
					</h2>
					{scale.items.map((item) => (
						<div
							key={item.id}
							style={{
								marginBottom: "1rem",
								padding: "0.75rem",
								border: "1px solid #eee",
								borderRadius: 4,
							}}
						>
							<p style={{ margin: 0, fontWeight: item.required ? 600 : 400 }}>
								{item.item_order}. {item.text}
								{item.required ? (
									<span style={{ color: "#b3261e" }}> *</span>
								) : null}
							</p>
							<ul style={{ margin: "0.5rem 0 0", paddingLeft: "1.2rem" }}>
								{item.response_options.map((option) => (
									<li key={option.id}>{option.label}</li>
								))}
							</ul>
						</div>
					))}
				</section>
			))}

			<footer style={{ marginTop: "2.5rem" }}>
				<Link
					href={`/catalogo/${params.instrumentId}/versiones/${params.versionId}`}
				>
					← Volver al detalle
				</Link>
				<p style={{ color: "#666", fontSize: "0.85rem", marginTop: "1rem" }}>
					Contenido sintético y de uso exclusivo para investigación
					(research-only).
				</p>
			</footer>
		</main>
	);
}
