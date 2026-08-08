"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { Notice } from "@/components/ui/Feedback";
import Button from "@/components/ui/Button";
import Field, { type FieldControlHandle } from "@/components/ui/Field";
import { ApiError, login } from "@/lib/auth";

import styles from "./page.module.css";

export default function LoginPage() {
	const router = useRouter();
	const passwordRef = useRef<FieldControlHandle>(null);
	const [username, setUsername] = useState("");
	const [password, setPassword] = useState("");
	const [error, setError] = useState<string | null>(null);
	const [busy, setBusy] = useState(false);

	async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
		event.preventDefault();
		if (busy) return;
		setBusy(true);
		setError(null);
		try {
			await login(username, password);
			setUsername("");
			setPassword("");
			router.push("/catalogo");
		} catch (err) {
			const isCredentialError =
				err instanceof ApiError &&
				["unauthorized", "invalid_credentials"].includes(err.payload.code);
			setError(
				isCredentialError
					? "El usuario o la contraseña no son correctos."
					: "No se pudo conectar con el servicio de la API. Intente nuevamente.",
			);
			passwordRef.current?.focus();
		} finally {
			setBusy(false);
		}
	}

	return (
		<div className={styles.page}>
			<section className={styles.panel} aria-labelledby="login-heading">
				<header className={styles.header}>
					<p className={styles.eyebrow}>Acceso al catálogo</p>
					<h1 id="login-heading">Iniciar sesión</h1>
					<p>
						Ingrese sus credenciales para administrar instrumentos y versiones.
					</p>
				</header>

				<form className={styles.form} onSubmit={onSubmit}>
					{error ? (
						<Notice tone="error" role="alert" message={error} />
					) : null}
					<Field
						id="login-username"
						name="username"
						label="Usuario"
						value={username}
						onChange={(event) => setUsername(event.target.value)}
						autoComplete="username"
						required
					/>
					<Field
						ref={passwordRef}
						id="login-password"
						name="password"
						label="Contraseña"
						type="password"
						value={password}
						onChange={(event) => setPassword(event.target.value)}
						autoComplete="current-password"
						required
					/>
					<Button
						type="submit"
						busy={busy}
						pendingLabel="Iniciando…"
					>
						Iniciar sesión
					</Button>
				</form>

				<div className={styles.footer}>
					<Link href="/">Volver al inicio</Link>
					<p>Datos sintéticos para investigación. No se realizan afirmaciones clínicas.</p>
				</div>
			</section>
		</div>
	);
}
