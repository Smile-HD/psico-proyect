"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, clearSession, getSessionUser, login } from "@/lib/auth";

export default function LoginPage() {
	const router = useRouter();
	const [username, setUsername] = useState("");
	const [password, setPassword] = useState("");
	const [error, setError] = useState<string | null>(null);
	const [busy, setBusy] = useState(false);

	async function onSubmit(event: React.FormEvent) {
		event.preventDefault();
		if (busy) return;
		setBusy(true);
		setError(null);
		try {
			const user = await login(username, password);
			const roles = user.roles.join(", ");
			setUsername("");
			setPassword("");
			router.push("/catalogo");
			setTimeout(
				() => alert(`Sesión iniciada como ${user.username} (${roles})`),
				0,
			);
		} catch (err) {
			if (err instanceof ApiError) {
				setError(err.payload.message);
			} else {
				setError("No se pudo conectar con el servicio de la API.");
			}
		} finally {
			setBusy(false);
		}
	}

	return (
		<main
			style={{
				fontFamily: "system-ui, sans-serif",
				maxWidth: 420,
				margin: "4rem auto",
				padding: "0 1rem",
			}}
		>
			<h1>TestPsico — Iniciar sesión</h1>
			<form
				onSubmit={onSubmit}
				style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}
			>
				<label>
					Usuario
					<input
						type="text"
						value={username}
						onChange={(event) => setUsername(event.target.value)}
						required
						style={{ display: "block", width: "100%", padding: "0.5rem" }}
					/>
				</label>
				<label>
					Contraseña
					<input
						type="password"
						value={password}
						onChange={(event) => setPassword(event.target.value)}
						required
						style={{ display: "block", width: "100%", padding: "0.5rem" }}
					/>
				</label>
				{error ? <p style={{ color: "#b3261e" }}>{error}</p> : null}
				<button
					type="submit"
					disabled={busy}
					style={{ padding: "0.6rem", cursor: "pointer" }}
				>
					{busy ? "Iniciando…" : "Iniciar sesión"}
				</button>
			</form>
			<footer style={{ marginTop: "2rem", color: "#666", fontSize: "0.9rem" }}>
				Entorno de desarrollo con datos sintéticos (research-only). Usuarios de
				prueba: admin, psicologo y evaluado.
			</footer>
		</main>
	);
}
