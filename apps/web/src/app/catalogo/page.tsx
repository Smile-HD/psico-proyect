"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import Button from "@/components/ui/Button";
import { ErrorState } from "@/components/ui/Feedback";
import EmptyState from "@/components/ui/EmptyState";
import Pagination from "@/components/ui/Pagination";
import Skeleton from "@/components/ui/Skeleton";
import StatusLabel, { type StatusKind } from "@/components/ui/StatusLabel";
import Table, { type TableColumn } from "@/components/ui/Table";
import { apiFetch, ApiError } from "@/lib/api";
import { useSessionUser } from "@/lib/auth";

import styles from "./page.module.css";

type InstrumentRow = {
	instrument_id: string;
	key: string;
	title: string;
	description: string | null;
	synthetic: boolean;
	source: string;
	status: string;
	version_no: number;
	instrument_version_id: string;
	published_at: string | null;
};

type ListResponse = {
	items: InstrumentRow[];
	page: number;
	page_size: number;
	total: number;
};

const FILTERS = [
	{ value: "all", label: "Todos" },
	{ value: "draft", label: "Borradores" },
	{ value: "published", label: "Publicados" },
	{ value: "archived", label: "Archivados" },
] as const;

const STATUS_LABEL: Record<string, { kind: StatusKind; label: string }> = {
	draft: { kind: "draft", label: "Borrador" },
	published: { kind: "published", label: "Publicada" },
	archived: { kind: "archived", label: "Archivada" },
};

function displayStatus(row: InstrumentRow) {
	if (row.source === "seed") {
		return { kind: "reference" as const, label: "Referencia · sintético" };
	}
	return (
		STATUS_LABEL[row.status] ?? { kind: "neutral" as const, label: row.status }
	);
}

export default function CatalogListPage() {
	const router = useRouter();
	const [rows, setRows] = useState<InstrumentRow[] | null>(null);
	const [total, setTotal] = useState(0);
	const [page, setPage] = useState(1);
	const [filter, setFilter] =
		useState<(typeof FILTERS)[number]["value"]>("all");
	const [error, setError] = useState<string | null>(null);
	const [reloadKey, setReloadKey] = useState(0);
	const { user, ready } = useSessionUser();
	const canManage = Boolean(
		user?.roles.includes("admin") || user?.roles.includes("psicologo"),
	);

	useEffect(() => {
		if (!ready) return;
		if (!user) {
			router.replace("/login");
			return;
		}
		if (!canManage) return;

		let cancelled = false;
		setRows(null);
		setError(null);
		const status = filter === "all" ? undefined : filter;
		const params = new URLSearchParams({ page: String(page), page_size: "20" });
		if (status) params.set("status", status);

		apiFetch<ListResponse>(
			`/api/v1/catalog/admin/instruments?${params.toString()}`,
			{ token: localStorage.getItem("psico_token") ?? "" },
		)
			.then((data) => {
				if (cancelled) return;
				setRows(data.items);
				setTotal(data.total);
			})
			.catch((err) => {
				if (cancelled) return;
				setError(
					err instanceof ApiError
						? "No se pudo cargar el catálogo. Revise el servicio y vuelva a intentar."
						: "No se pudo cargar el catálogo. Intente nuevamente.",
				);
			})
			.catch(() => undefined);

		return () => {
			cancelled = true;
		};
	}, [canManage, filter, page, ready, reloadKey, router, user]);

	const columns: readonly TableColumn<InstrumentRow>[] = [
		{
			id: "key",
			header: "Clave",
			rowHeader: true,
			render: (row) => <span>{row.key}</span>,
		},
		{
			id: "title",
			header: "Título",
			render: (row) => row.title,
		},
		{
			id: "status",
			header: "Estado",
			render: (row) => {
				const status = displayStatus(row);
				return <StatusLabel kind={status.kind}>{status.label}</StatusLabel>;
			},
		},
		{
			id: "version",
			header: "Versión",
			numeric: true,
			render: (row) => `v${row.version_no}`,
		},
		{
			id: "actions",
			header: "Acciones",
			render: (row) => (
				<Link
					className={styles.tableLink}
					href={`/catalogo/${row.instrument_id}/versiones/${row.instrument_version_id}`}
				>
					{row.source === "seed" || row.status !== "draft" ? "Ver" : "Editar"}
				</Link>
			),
		},
	];

	if (ready && user && !canManage) {
		return (
			<div className={styles.page}>
				<EmptyState
					contextLabel="Catálogo de instrumentos"
					title="Sección no disponible"
					description="Su cuenta puede participar en evaluaciones, pero no tiene permisos para administrar instrumentos."
				/>
			</div>
		);
	}

	return (
		<div className={styles.page}>
			<header className={styles.header}>
				<div>
					<p className={styles.eyebrow}>Administración</p>
					<h1>Catálogo de instrumentos</h1>
					<p className={styles.intro}>
						Consulte las versiones disponibles y mantenga el contenido editable.
					</p>
				</div>
				{canManage ? (
					<Link className={styles.linkButton} href="/catalogo/nuevo">
						Nuevo instrumento
					</Link>
				) : null}
			</header>

			<nav className={styles.filters} aria-label="Filtrar instrumentos">
				{FILTERS.map((option) => (
					<Button
						key={option.value}
						size="compact"
						variant={filter === option.value ? "primary" : "secondary"}
						type="button"
						aria-pressed={filter === option.value}
						onClick={() => {
							setFilter(option.value);
							setPage(1);
						}}
					>
						{option.label}
					</Button>
				))}
			</nav>

			{!ready || !user ? (
				<Skeleton
					variant="table"
					rows={5}
					columns={5}
					label="Cargando el catálogo…"
				/>
			) : error ? (
				<ErrorState
					title="No se pudo cargar el catálogo"
					message={error}
					onRetry={() => setReloadKey((current) => current + 1)}
				/>
			) : rows === null ? (
				<Skeleton
					variant="table"
					rows={5}
					columns={5}
					label="Cargando el catálogo…"
				/>
			) : rows.length === 0 ? (
				<EmptyState
					contextLabel={`${total} resultados`}
					title="No hay instrumentos todavía"
					description={
						filter === "all"
							? "El catálogo está vacío. Puede crear el primer instrumento para comenzar."
							: "No hay instrumentos con este filtro. Pruebe otra vista o cree un instrumento nuevo."
					}
					action={
						canManage ? (
							<Link className={styles.linkButton} href="/catalogo/nuevo">
								Crear instrumento
							</Link>
						) : undefined
					}
				/>
			) : (
				<section className={styles.results} aria-labelledby="results-heading">
					<div className={styles.resultsHeading}>
						<h2 id="results-heading">Instrumentos</h2>
						<p className={styles.resultCount}>
							{total} instrumento{total === 1 ? "" : "s"} · página {page}
						</p>
					</div>
					<Table
						caption="Instrumentos del catálogo"
						columns={columns}
						rows={rows}
						rowKey={(row) => row.instrument_version_id}
					/>
					<Pagination
						page={page}
						pageSize={20}
						total={total}
						onPageChange={setPage}
					/>
				</section>
			)}
		</div>
	);
}
