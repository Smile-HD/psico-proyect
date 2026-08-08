"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { clearSession, getSessionUser } from "@/lib/auth";

type InstrumentRow = {
  id: string;
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

const FILTERS: Record<string, string> = {
  all: "Todos",
  draft: "Borradores",
  published: "Publicados",
  archived: "Archivados",
};

const STATUS_LABEL: Record<string, string> = {
  draft: "Borrador",
  published: "Publicada",
  archived: "Archivada",
};

export default function CatalogListPage() {
  const router = useRouter();
  const [rows, setRows] = useState<InstrumentRow[] | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const user = getSessionUser();
  const canManage = user?.roles.includes("admin") || user?.roles.includes("psicologo");

  useEffect(() => {
    if (!canManage) {
      router.replace("/");
      return;
    }
    let cancelled = false;
    setBusy(true);
    const status = filter === "all" ? undefined : filter;
    const params = new URLSearchParams({ page: String(page), page_size: "20" });
    if (status) params.set("status", status);
    apiFetch<ListResponse>(`/api/v1/catalog/admin/instruments?${params.toString()}`, {
      token: localStorage.getItem("psico_token") ?? "",
    })
      .then((data) => {
        if (cancelled) return;
        setRows(data.items);
        setTotal(data.total);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setRows([]);
        setError(err instanceof ApiError ? err.payload.message : "No se pudo cargar el catálogo.");
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [page, filter, canManage, router]);

  function onLogout() {
    clearSession();
    router.replace("/login");
  }

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", maxWidth: 900, margin: "2rem auto", padding: "0 1rem" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>Catálogo de instrumentos</h1>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          {user ? <span style={{ color: "#666" }}>{user.username}</span> : null}
          <button onClick={onLogout} style={{ cursor: "pointer" }}>Salir</button>
        </div>
      </header>

      <nav style={{ display: "flex", gap: "1rem", margin: "1rem 0" }}>
        {Object.entries(FILTERS).map(([value, label]) => (
          <button
            key={value}
            onClick={() => {
              setFilter(value);
              setPage(1);
            }}
            style={{
              cursor: "pointer",
              fontWeight: filter === value ? "bold" : "normal",
              padding: "0.4rem 0.8rem",
            }}
          >
            {label}
          </button>
        ))}
        {canManage ? (
          <Link href="/catalogo/nuevo" style={{ marginLeft: "auto", fontWeight: "bold" }}>
            + Nuevo instrumento
          </Link>
        ) : null}
      </nav>

      {error ? <p style={{ color: "#b3261e" }}>{error}</p> : null}
      {busy && !rows ? <p>Cargando…</p> : null}

      {rows ? (
        <>
          <p style={{ color: "#666" }}>
            {total} instrumento{total === 1 ? "" : "s"} · página {page}
          </p>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #ccc" }}>
                <th style={{ padding: "0.5rem" }}>Clave</th>
                <th style={{ padding: "0.5rem" }}>Título</th>
                <th style={{ padding: "0.5rem" }}>Estado</th>
                <th style={{ padding: "0.5rem" }}>Versión</th>
                <th style={{ padding: "0.5rem" }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={{ padding: "0.5rem" }}>
                    {row.key}
                    {row.source === "seed" ? (
                      <span
                        title="Instrumento de referencia (sintético)"
                        style={{ marginLeft: "0.4rem", color: "#8a5a00", fontSize: "0.8rem" }}
                      >
                        referencia
                      </span>
                    ) : null}
                  </td>
                  <td style={{ padding: "0.5rem" }}>{row.title}</td>
                  <td style={{ padding: "0.5rem" }}>{STATUS_LABEL[row.status] ?? row.status}</td>
                  <td style={{ padding: "0.5rem" }}>v{row.version_no}</td>
                  <td style={{ padding: "0.5rem" }}>
                    <Link href={`/catalogo/${row.id}/versiones/${row.instrument_version_id}`}>
                      {row.source === "seed" ? "Ver" : row.status === "draft" ? "Editar" : "Ver"}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem" }}>
            <button disabled={page <= 1} onClick={() => setPage(page - 1)} style={{ cursor: "pointer" }}>
              Anterior
            </button>
            <button disabled={page * 20 >= total} onClick={() => setPage(page + 1)} style={{ cursor: "pointer" }}>
              Siguiente
            </button>
          </div>
        </>
      ) : null}
    </main>
  );
}
