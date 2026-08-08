"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { useSessionUser } from "@/lib/auth";

type CreateResponse = {
	instrument: { id: string };
	draft: { instrument_version_id: string };
};

export default function NewInstrumentPage() {
	const router = useRouter();
	const [key, setKey] = useState("");
	const [title, setTitle] = useState("");
	const [description, setDescription] = useState("");
	const [error, setError] = useState<string | null>(null);
	const [busy, setBusy] = useState(false);
	const { user, ready } = useSessionUser();
	const canManage =
		user?.roles.includes("admin") || user?.roles.includes("psicologo");

	async function onSubmit(event: React.FormEvent) {
		event.preventDefault();
		if (busy) return;
		if (!/^[A-Z0-9_.-]+$/.test(key)) {
			setError(
				"La clave solo admite mayúsculas, números, punto, guion bajo y guion medio.",
			);
			return;
		}
		setBusy(true);
		setError(null);
		try {
			const created = await apiFetch<CreateResponse>(
				"/api/v1/catalog/admin/instruments",
				{
					method: "POST",
					token: localStorage.getItem("psico_token") ?? "",
					idempotencyKey: crypto.randomUUID(),
					body: {
						key,
						title,
						description: description.trim() ? description : null,
					},
				},
			);
			router.push(
				`/catalogo/${created.instrument.id}/versiones/${created.draft.instrument_version_id}`,
			);
		} catch (err) {
			setError(
				err instanceof ApiError
					? err.payload.message
					: "No se pudo crear el instrumento.",
			);
			setBusy(false);
		}
	}

	if (ready && !canManage) {
		return (
			<p style={{ fontFamily: "system-ui, sans-serif", padding: "2rem" }}>
				No tiene permisos para esta sección.
			</p>
		);
	}

	return (
		<main
			style={{
				fontFamily: "system-ui, sans-serif",
				maxWidth: 640,
				margin: "2rem auto",
				padding: "0 1rem",
			}}
		>
			<h1>Nuevo instrumento</h1>
			<form
				onSubmit={onSubmit}
				style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}
			>
				<label>
					Clave (única, mayúsculas)
					<input
						type="text"
						value={key}
						onChange={(event) => setKey(event.target.value.toUpperCase())}
						required
						pattern="[A-Z0-9_.-]+"
						placeholder="EJ: CAT-01"
						style={{ display: "block", width: "100%", padding: "0.5rem" }}
					/>
				</label>
				<label>
					Título
					<input
						type="text"
						value={title}
						onChange={(event) => setTitle(event.target.value)}
						required
						style={{ display: "block", width: "100%", padding: "0.5rem" }}
					/>
				</label>
				<label>
					Descripción (opcional)
					<textarea
						value={description}
						onChange={(event) => setDescription(event.target.value)}
						rows={3}
						style={{ display: "block", width: "100%", padding: "0.5rem" }}
					/>
				</label>
				{error ? <p style={{ color: "#b3261e" }}>{error}</p> : null}
				<div style={{ display: "flex", gap: "0.5rem" }}>
					<button
						type="submit"
						disabled={busy}
						style={{ padding: "0.6rem", cursor: "pointer" }}
					>
						{busy ? "Creando…" : "Crear instrumento"}
					</button>
					<button
						type="button"
						onClick={() => router.push("/catalogo")}
						style={{ padding: "0.6rem", cursor: "pointer" }}
					>
						Cancelar
					</button>
				</div>
			</form>
			<p style={{ color: "#666", fontSize: "0.9rem" }}>
				El instrumento semilla de referencia (TP-S-01) no aparece como base: el
				contenido semilla es de solo lectura.
			</p>
		</main>
	);
}
