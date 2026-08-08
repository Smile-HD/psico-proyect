"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import Button from "@/components/ui/Button";
import { Notice } from "@/components/ui/Feedback";
import EmptyState from "@/components/ui/EmptyState";
import Field, { type FieldControlHandle } from "@/components/ui/Field";
import Skeleton from "@/components/ui/Skeleton";
import { apiFetch, ApiError } from "@/lib/api";
import { useSessionUser } from "@/lib/auth";

import styles from "./page.module.css";

type CreateResponse = {
	instrument: { id: string };
	draft: { instrument_version_id: string };
};

type FieldErrors = {
	key?: string;
	title?: string;
};

const KEY_PATTERN = /^[A-Z0-9_.-]+$/;
const KEY_HELP =
	"Use mayúsculas, números, punto, guion bajo o guion medio. Ejemplo: CAT-01.";

export default function NewInstrumentPage() {
	const router = useRouter();
	const keyRef = useRef<FieldControlHandle>(null);
	const titleRef = useRef<FieldControlHandle>(null);
	const [key, setKey] = useState("");
	const [title, setTitle] = useState("");
	const [description, setDescription] = useState("");
	const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
	const [formError, setFormError] = useState<string | null>(null);
	const [busy, setBusy] = useState(false);
	const { user, ready } = useSessionUser();
	const canManage = Boolean(
		user?.roles.includes("admin") || user?.roles.includes("psicologo"),
	);

	useEffect(() => {
		if (ready && !user) {
			router.replace("/login");
		}
	}, [ready, router, user]);

	function validateFields(): FieldErrors {
		const nextErrors: FieldErrors = {};
		if (!KEY_PATTERN.test(key)) {
			nextErrors.key =
				"La clave debe usar solo mayúsculas, números, punto, guion bajo o guion medio.";
		}
		if (!title.trim()) {
			nextErrors.title = "Ingrese un título para el instrumento.";
		}
		return nextErrors;
	}

	async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
		event.preventDefault();
		if (busy) return;
		const nextErrors = validateFields();
		setFieldErrors(nextErrors);
		setFormError(null);
		const firstInvalid = nextErrors.key ? keyRef : nextErrors.title ? titleRef : null;
		if (firstInvalid) {
			firstInvalid.current?.focus();
			return;
		}

		setBusy(true);
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
			setFormError(
				err instanceof ApiError
					? "No se pudo crear el instrumento. Revise los datos e intente nuevamente."
					: "No se pudo conectar con el servicio. Intente nuevamente.",
			);
			setBusy(false);
		}
	}

	if (!ready || !user) {
		return (
			<div className={styles.page}>
				<Skeleton variant="block" label="Cargando el formulario…" />
			</div>
		);
	}

	if (!canManage) {
		return (
			<div className={styles.page}>
				<EmptyState
					contextLabel="Nuevo instrumento"
					title="No puede crear instrumentos"
					description="Su cuenta no tiene permisos de administración. Solicite acceso a una persona administradora del catálogo."
				/>
			</div>
		);
	}

	return (
		<div className={styles.page}>
			<header className={styles.header}>
				<p className={styles.eyebrow}>Catálogo · alta</p>
				<h1>Nuevo instrumento</h1>
				<p>
					Registre los datos iniciales. El contenido de la versión se completa después.
				</p>
			</header>

			<form className={styles.form} onSubmit={onSubmit} noValidate>
				{formError ? <Notice tone="error" role="alert" message={formError} /> : null}
				<Field
					ref={keyRef}
					id="instrument-key"
					name="key"
					label="Clave"
					value={key}
					onChange={(event) => {
						setKey(event.target.value.toUpperCase());
						if (fieldErrors.key) {
							setFieldErrors((current) => ({ ...current, key: undefined }));
						}
					}}
					helperText={KEY_HELP}
					error={fieldErrors.key}
					required
					placeholder="CAT-01"
					pattern="[A-Z0-9_.-]+"
				/>
				<Field
					ref={titleRef}
					id="instrument-title"
					name="title"
					label="Título"
					value={title}
					onChange={(event) => {
						setTitle(event.target.value);
						if (fieldErrors.title) {
							setFieldErrors((current) => ({ ...current, title: undefined }));
						}
					}}
					error={fieldErrors.title}
					required
				/>
				<Field
					id="instrument-description"
					name="description"
					label="Descripción"
					control="textarea"
					value={description}
					onChange={(event) => setDescription(event.target.value)}
					helperText="Opcional. Describa el propósito de investigación de este instrumento."
					rows={4}
				/>
				<div className={styles.actions}>
					<Button type="submit" busy={busy} pendingLabel="Creando…">
						Crear instrumento
					</Button>
					<Button
						type="button"
						variant="secondary"
						onClick={() => router.push("/catalogo")}
					>
						Cancelar
					</Button>
				</div>
			</form>
		</div>
	);
}
