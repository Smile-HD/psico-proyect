"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import Breadcrumb from "@/components/ui/Breadcrumb";
import Button from "@/components/ui/Button";
import { ErrorState, Notice } from "@/components/ui/Feedback";
import Dialog from "@/components/ui/Dialog";
import Field from "@/components/ui/Field";
import Skeleton from "@/components/ui/Skeleton";
import StatusLabel, { type StatusKind } from "@/components/ui/StatusLabel";
import { apiFetch, ApiError } from "@/lib/api";
import { useSessionUser } from "@/lib/auth";

import styles from "./page.module.css";

type OptionDraft = {
	id?: string;
	display_order: number;
	label: string;
	locale: string;
};

type ItemDraft = {
	id?: string;
	item_order: number;
	text: string;
	locale: string;
	required: boolean;
	options: OptionDraft[];
};

type ScaleDraft = {
	id?: string;
	label: string;
	locale: string;
	display_order: number;
	items: ItemDraft[];
};

type AdminVersionDetail = {
	instrument_version_id: string;
	instrument_id: string;
	instrument_key: string;
	title: string;
	description: string | null;
	version_no: number;
	status: "draft" | "published" | "archived";
	source: "seed" | "runtime";
	published_at: string | null;
	response_type: string;
	scales: ScaleDraft[];
};

type ApiOption = {
	id?: string;
	display_order: number;
	label: string;
	locale: string;
};

type ApiItem = {
	id?: string;
	item_order: number;
	text: string;
	locale: string;
	required: boolean;
	response_options: ApiOption[];
};

type ApiScale = {
	id?: string;
	label: string;
	locale: string;
	display_order: number;
	items: ApiItem[];
};

type ApiDetail = Omit<AdminVersionDetail, "scales"> & { scales: ApiScale[] };

type DialogAction = "publish" | "archive";

function toDraft(detail: ApiDetail): AdminVersionDetail {
	return {
		...detail,
		scales: detail.scales.map((scale) => ({
			id: scale.id,
			label: scale.label,
			locale: scale.locale,
			display_order: scale.display_order,
			items: scale.items.map((item) => ({
				id: item.id,
				item_order: item.item_order,
				text: item.text,
				locale: item.locale,
				required: item.required,
				options: item.response_options.map((option) => ({
					id: option.id,
					display_order: option.display_order,
					label: option.label,
					locale: option.locale,
				})),
			})),
		})),
	};
}

const OPTION_COUNT = 5;
const NEUTRAL_OPTIONS = [
	"Nunca",
	"Casi nunca",
	"A veces",
	"Casi siempre",
	"Siempre",
];

function emptyScale(order: number): ScaleDraft {
	return {
		label: "",
		locale: "es",
		display_order: order,
		items: [
			{
				item_order: 1,
				text: "",
				locale: "es",
				required: true,
				options: NEUTRAL_OPTIONS.map((label, index) => ({
					display_order: index + 1,
					label,
					locale: "es",
				})),
			},
		],
	};
}

function statusFor(status: AdminVersionDetail["status"]) {
	const labels: Record<
		AdminVersionDetail["status"],
		{ kind: StatusKind; label: string }
	> = {
		draft: { kind: "draft", label: "Borrador" },
		published: { kind: "published", label: "Publicada" },
		archived: { kind: "archived", label: "Archivada" },
	};
	return labels[status];
}

export default function VersionEditorPage() {
	const params = useParams<{ instrumentId: string; versionId: string }>();
	const router = useRouter();
	const [detail, setDetail] = useState<AdminVersionDetail | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [notice, setNotice] = useState<string | null>(null);
	const [busy, setBusy] = useState(false);
	const [reloadKey, setReloadKey] = useState(0);
	const [dialogAction, setDialogAction] = useState<DialogAction | null>(null);
	const { user, ready } = useSessionUser();
	const canManage = Boolean(
		user?.roles.includes("admin") || user?.roles.includes("psicologo"),
	);
	const isAdmin = user?.roles.includes("admin") ?? false;
	const readOnly = Boolean(
		detail && (detail.status !== "draft" || detail.source === "seed"),
	);
	const canPublish = Boolean(
		isAdmin && detail?.status === "draft" && detail.source === "runtime",
	);
	const canArchive = Boolean(
		canManage && detail?.status === "published" && detail.source === "runtime",
	);
	const readOnlyDescriptionId = "editor-read-only-description";

	useEffect(() => {
		if (!ready) return;
		if (!canManage) {
			router.replace("/login");
			return;
		}

		let cancelled = false;
		setDetail(null);
		setError(null);
		apiFetch<ApiDetail>(`/api/v1/catalog/admin/versions/${params.versionId}`, {
			token: localStorage.getItem("psico_token") ?? "",
		})
			.then((data) => {
				if (!cancelled) setDetail(toDraft(data));
			})
			.catch((err) => {
				if (cancelled) return;
				setError(
					err instanceof ApiError && err.payload.code.includes("not_found")
						? "No se encontró esta versión del instrumento."
						: "No se pudo cargar la versión. Revise el servicio e intente nuevamente.",
				);
			});
		return () => {
			cancelled = true;
		};
	}, [canManage, params.versionId, ready, reloadKey, router]);

	function updateScale(orderIndex: number, patch: Partial<ScaleDraft>) {
		setDetail((current) => {
			if (!current) return current;
			return {
				...current,
				scales: current.scales.map((scale, index) =>
					index === orderIndex ? { ...scale, ...patch } : scale,
				),
			};
		});
	}

	function updateItem(
		scaleIndex: number,
		itemIndex: number,
		patch: Partial<ItemDraft>,
	) {
		setDetail((current) => {
			if (!current) return current;
			return {
				...current,
				scales: current.scales.map((scale, index) =>
					index !== scaleIndex
						? scale
						: {
								...scale,
								items: scale.items.map((item, itemIndexInScale) =>
									itemIndexInScale === itemIndex ? { ...item, ...patch } : item,
								),
							},
				),
			};
		});
	}

	function updateOption(
		scaleIndex: number,
		itemIndex: number,
		optionIndex: number,
		label: string,
	) {
		setDetail((current) => {
			if (!current) return current;
			return {
				...current,
				scales: current.scales.map((scale, scaleIndexInDetail) => {
					if (scaleIndexInDetail !== scaleIndex) return scale;
					return {
						...scale,
						items: scale.items.map((item, itemIndexInScale) => {
							if (itemIndexInScale !== itemIndex) return item;
							return {
								...item,
								options: item.options.map((option, optionIndexInItem) =>
									optionIndexInItem === optionIndex
										? { ...option, label }
										: option,
								),
							};
						}),
					};
				}),
			};
		});
	}

	function addScale() {
		setDetail((current) =>
			current
				? {
						...current,
						scales: [...current.scales, emptyScale(current.scales.length + 1)],
					}
				: current,
		);
	}

	function removeScale(index: number) {
		setDetail((current) => {
			if (!current) return current;
			return {
				...current,
				scales: current.scales
					.filter((_, scaleIndex) => scaleIndex !== index)
					.map((scale, scaleIndex) => ({
						...scale,
						display_order: scaleIndex + 1,
					})),
			};
		});
	}

	function addItem(scaleIndex: number) {
		setDetail((current) => {
			if (!current) return current;
			return {
				...current,
				scales: current.scales.map((scale, index) =>
					index !== scaleIndex
						? scale
						: {
								...scale,
								items: [
									...scale.items,
									{
										item_order: scale.items.length + 1,
										text: "",
										locale: "es",
										required: true,
										options: NEUTRAL_OPTIONS.map((label, optionIndex) => ({
											display_order: optionIndex + 1,
											label,
											locale: "es",
										})),
									},
								],
							},
				),
			};
		});
	}

	function removeItem(scaleIndex: number, itemIndex: number) {
		setDetail((current) => {
			if (!current) return current;
			return {
				...current,
				scales: current.scales.map((scale, index) =>
					index !== scaleIndex
						? scale
						: {
								...scale,
								items: scale.items
									.filter(
										(_, currentItemIndex) => currentItemIndex !== itemIndex,
									)
									.map((item, currentItemIndex) => ({
										...item,
										item_order: currentItemIndex + 1,
									})),
							},
				),
			};
		});
	}

	function validate(): string | null {
		if (!detail) return "No hay contenido cargado.";
		if (detail.scales.length === 0) return "Agregue al menos una escala.";
		for (const scale of detail.scales) {
			if (!scale.label.trim()) return "Toda escala necesita un nombre.";
			if (scale.items.length === 0) {
				return `La escala «${scale.label}» necesita al menos un ítem.`;
			}
			for (const item of scale.items) {
				if (!item.text.trim())
					return `La escala «${scale.label}» tiene un ítem sin texto.`;
				if (item.options.length !== OPTION_COUNT) {
					return `El ítem «${item.text}» debe tener exactamente ${OPTION_COUNT} opciones.`;
				}
				for (const option of item.options) {
					if (!option.label.trim()) {
						return `El ítem «${item.text}» tiene una opción sin etiqueta.`;
					}
				}
			}
		}
		return null;
	}

	async function saveDraft() {
		if (busy || !detail) return;
		const validation = validate();
		if (validation) {
			setError(validation);
			return;
		}
		setBusy(true);
		setError(null);
		setNotice(null);
		try {
			await apiFetch(
				`/api/v1/catalog/admin/versions/${params.versionId}/content`,
				{
					method: "PUT",
					token: localStorage.getItem("psico_token") ?? "",
					idempotencyKey: crypto.randomUUID(),
					body: {
						response_type: detail.response_type,
						scales: detail.scales.map((scale) => ({
							...(scale.id ? { id: scale.id } : {}),
							label: scale.label,
							locale: scale.locale,
							display_order: scale.display_order,
							items: scale.items.map((item) => ({
								...(item.id ? { id: item.id } : {}),
								item_order: item.item_order,
								text: item.text,
								locale: item.locale,
								required: item.required,
								options: item.options.map((option) => ({
									...(option.id ? { id: option.id } : {}),
									display_order: option.display_order,
									label: option.label,
									locale: option.locale,
								})),
							})),
						})),
					},
				},
			);
			setNotice("Borrador guardado");
		} catch (err) {
			setError(
				err instanceof ApiError
					? "No se pudo guardar el borrador. Revise los datos e intente nuevamente."
					: "No se pudo conectar con el servicio. Intente nuevamente.",
			);
		} finally {
			setBusy(false);
		}
	}

	function requestLifecycleAction(action: DialogAction) {
		if (busy || !detail) return;
		if (action === "publish") {
			const validation = validate();
			if (validation) {
				setError(validation);
				return;
			}
		}
		setError(null);
		setNotice(null);
		setDialogAction(action);
	}

	async function confirmLifecycleAction() {
		if (busy || !detail || !dialogAction) return;
		const action = dialogAction;
		setBusy(true);
		setError(null);
		try {
			await apiFetch(
				`/api/v1/catalog/admin/versions/${params.versionId}/${action}`,
				{
					method: "POST",
					token: localStorage.getItem("psico_token") ?? "",
					idempotencyKey: crypto.randomUUID(),
				},
			);
			setNotice(
				action === "publish"
					? "Versión publicada. La publicación es inmutable."
					: "Versión archivada.",
			);
			const refreshed = await apiFetch<ApiDetail>(
				`/api/v1/catalog/admin/versions/${params.versionId}`,
				{ token: localStorage.getItem("psico_token") ?? "" },
			);
			setDetail(toDraft(refreshed));
		} catch (err) {
			setError(
				err instanceof ApiError
					? "No se pudo actualizar el estado de la versión. Intente nuevamente."
					: "No se pudo conectar con el servicio. Intente nuevamente.",
			);
		} finally {
			setBusy(false);
			setDialogAction(null);
		}
	}

	if (!ready || !user || !canManage) {
		return (
			<div className={styles.page}>
				<Skeleton variant="block" label="Cargando el editor…" />
			</div>
		);
	}

	if (error && !detail) {
		return (
			<div className={styles.page}>
				<ErrorState
					title="No se pudo cargar la versión"
					message={error}
					onRetry={() => setReloadKey((current) => current + 1)}
					backAction={<Link href="/catalogo">Volver al catálogo</Link>}
				/>
			</div>
		);
	}

	if (!detail) {
		return (
			<div className={styles.page}>
				<Skeleton variant="block" label="Cargando el editor…" />
			</div>
		);
	}

	const status = statusFor(detail.status);
	const dialogTitle =
		dialogAction === "publish" ? "Publicar versión" : "Archivar versión";
	const dialogDescription =
		dialogAction === "publish"
			? "La publicación congela el contenido y la versión ya no podrá editarse."
			: "El archivo conserva el historial y retira esta versión del catálogo activo.";

	return (
		<div className={styles.page}>
			<Breadcrumb
				items={[
					{ label: "Catálogo", href: "/catalogo" },
					{ label: detail.instrument_key },
					{ label: `Versión ${detail.version_no}`, current: true },
				]}
			/>

			<header className={styles.header}>
				<div>
					<p className={styles.eyebrow}>Editor de versión</p>
					<h1>
						{detail.title}{" "}
						<span className={styles.key}>({detail.instrument_key})</span>
					</h1>
					<p className={styles.meta}>
						<span className={styles.version}>v{detail.version_no}</span>
						{detail.published_at
							? ` · publicada el ${new Date(detail.published_at).toLocaleString("es-ES")}`
							: null}
					</p>
				</div>
				<StatusLabel
					kind={status.kind}
					symbol={detail.source === "seed" ? "·" : undefined}
				>
					{detail.source === "seed" ? "Referencia · sintético" : status.label}
				</StatusLabel>
			</header>

			{readOnly ? (
				<p id={readOnlyDescriptionId} className={styles.readOnlyNotice}>
					{detail.source === "seed"
						? "Esta versión de referencia es de solo lectura y no se puede editar."
						: "La versión publicada es inmutable y no se puede editar."}
				</p>
			) : null}
			{error ? <Notice tone="error" role="alert" message={error} /> : null}
			{notice ? <Notice tone="success" role="status" message={notice} /> : null}

			<section className={styles.content} aria-labelledby="scales-heading">
				<div className={styles.sectionHeader}>
					<div>
						<p className={styles.kicker}>Contenido</p>
						<h2 id="scales-heading">Escalas</h2>
					</div>
					{!readOnly ? (
						<Button
							type="button"
							size="compact"
							variant="secondary"
							onClick={addScale}
						>
							Agregar escala
						</Button>
					) : null}
				</div>

				{detail.scales.map((scale, scaleIndex) => (
					<fieldset
						className={styles.scale}
						key={scale.id ?? `scale-${scaleIndex}`}
					>
						<legend className={styles.legend}>
							<span>Escala {scale.display_order}</span>
							{!readOnly ? (
								<Button
									type="button"
									size="compact"
									variant="ghost"
									onClick={() => removeScale(scaleIndex)}
								>
									Quitar escala
								</Button>
							) : null}
						</legend>
						<Field
							id={`scale-${scaleIndex}-label`}
							label="Nombre de la escala"
							value={scale.label}
							onChange={(event) =>
								updateScale(scaleIndex, { label: event.target.value })
							}
							disabled={readOnly}
							aria-describedby={readOnly ? readOnlyDescriptionId : undefined}
							required
						/>

						<div className={styles.items}>
							{scale.items.map((item, itemIndex) => (
								<fieldset
									className={styles.item}
									key={item.id ?? `item-${scaleIndex}-${itemIndex}`}
								>
									<legend className={styles.legend}>
										<span>Ítem {item.item_order}</span>
										{!readOnly ? (
											<Button
												type="button"
												size="compact"
												variant="ghost"
												onClick={() => removeItem(scaleIndex, itemIndex)}
											>
												Quitar ítem
											</Button>
										) : null}
									</legend>
									<Field
										id={`scale-${scaleIndex}-item-${itemIndex}-text`}
										label="Texto del ítem"
										value={item.text}
										onChange={(event) =>
											updateItem(scaleIndex, itemIndex, {
												text: event.target.value,
											})
										}
										disabled={readOnly}
										aria-describedby={
											readOnly ? readOnlyDescriptionId : undefined
										}
										required
									/>
									<Field
										id={`scale-${scaleIndex}-item-${itemIndex}-required`}
										label="Ítem obligatorio"
										control="checkbox"
										checked={item.required}
										onChange={(event) =>
											updateItem(scaleIndex, itemIndex, {
												required: (event.target as HTMLInputElement).checked,
											})
										}
										disabled={readOnly}
										aria-describedby={
											readOnly ? readOnlyDescriptionId : undefined
										}
									/>

									<fieldset className={styles.options}>
										<legend>Opciones de respuesta</legend>
										{item.options.map((option, optionIndex) => (
											<Field
												key={
													option.id ??
													`option-${scaleIndex}-${itemIndex}-${optionIndex}`
												}
												id={`scale-${scaleIndex}-item-${itemIndex}-option-${optionIndex}`}
												label={`Opción ${option.display_order}`}
												value={option.label}
												onChange={(event) =>
													updateOption(
														scaleIndex,
														itemIndex,
														optionIndex,
														event.target.value,
													)
												}
												disabled={readOnly}
												aria-describedby={
													readOnly ? readOnlyDescriptionId : undefined
												}
											/>
										))}
									</fieldset>
								</fieldset>
							))}
						</div>
						{!readOnly ? (
							<Button
								type="button"
								size="compact"
								variant="secondary"
								onClick={() => addItem(scaleIndex)}
							>
								Agregar ítem
							</Button>
						) : null}
					</fieldset>
				))}
			</section>

			<footer className={styles.actions}>
				{!readOnly ? (
					<Button
						type="button"
						busy={busy}
						pendingLabel="Guardando…"
						onClick={saveDraft}
					>
						Guardar borrador
					</Button>
				) : null}
				{canPublish ? (
					<Button
						type="button"
						variant="secondary"
						disabled={busy}
						onClick={() => requestLifecycleAction("publish")}
					>
						Publicar versión
					</Button>
				) : null}
				{canArchive ? (
					<Button
						type="button"
						variant="danger"
						disabled={busy}
						onClick={() => requestLifecycleAction("archive")}
					>
						Archivar versión
					</Button>
				) : null}
				{detail.status === "published" ? (
					<Link
						className={styles.secondaryLink}
						href={`/catalogo/${params.instrumentId}/versiones/${params.versionId}/vista`}
					>
						Ver vista del evaluado
					</Link>
				) : null}
			</footer>

			<Dialog
				open={dialogAction !== null}
				title={dialogTitle}
				description={dialogDescription}
				onClose={() => {
					if (!busy) setDialogAction(null);
				}}
			>
				<Button
					type="button"
					variant="secondary"
					disabled={busy}
					data-dialog-cancel
					onClick={() => setDialogAction(null)}
				>
					Cancelar
				</Button>
				<Button
					type="button"
					variant={dialogAction === "archive" ? "danger" : "primary"}
					busy={busy}
					pendingLabel={
						dialogAction === "archive" ? "Archivando…" : "Publicando…"
					}
					data-dialog-confirm
					onClick={confirmLifecycleAction}
				>
					{dialogAction === "archive"
						? "Confirmar archivo"
						: "Confirmar publicación"}
				</Button>
			</Dialog>
		</div>
	);
}
