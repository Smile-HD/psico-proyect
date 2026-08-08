"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { getSessionUser } from "@/lib/auth";

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

const OPTION_COUNT = 5;
const NEUTRAL_OPTIONS = ["Nunca", "Casi nunca", "A veces", "Casi siempre", "Siempre"];

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

export default function VersionEditorPage() {
  const params = useParams<{ instrumentId: string; versionId: string }>();
  const router = useRouter();
  const [detail, setDetail] = useState<AdminVersionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const user = getSessionUser();
  const canManage = user?.roles.includes("admin") || user?.roles.includes("psicologo");
  const isAdmin = user?.roles.includes("admin") ?? false;
  const readOnly = detail !== null && (detail.status !== "draft" || detail.source === "seed");
  const canPublish = isAdmin && detail?.status === "draft" && detail.source === "runtime";
  const canArchive =
    canManage && detail?.status === "published" && detail.source === "runtime";

  useEffect(() => {
    if (!canManage) {
      router.replace("/");
      return;
    }
    let cancelled = false;
    apiFetch<AdminVersionDetail>(
      `/api/v1/catalog/admin/versions/${params.versionId}`,
      { token: localStorage.getItem("psico_token") ?? "" },
    )
      .then((data) => {
        if (!cancelled) setDetail(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.payload.message : "No se pudo cargar la versión.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [params.versionId, canManage, router]);

  function updateScale(orderIndex: number, patch: Partial<ScaleDraft>) {
    setDetail((current) => {
      if (!current) return current;
      const scales = current.scales.map((scale, index) =>
        index === orderIndex ? { ...scale, ...patch } : scale,
      );
      return { ...current, scales };
    });
  }

  function updateItem(scaleIndex: number, itemIndex: number, patch: Partial<ItemDraft>) {
    setDetail((current) => {
      if (!current) return current;
      const scales = current.scales.map((scale, index) => {
        if (index !== scaleIndex) return scale;
        const items = scale.items.map((item, j) => (j === itemIndex ? { ...item, ...patch } : item));
        return { ...scale, items };
      });
      return { ...current, scales };
    });
  }

  function updateOption(scaleIndex: number, itemIndex: number, optionIndex: number, label: string) {
    setDetail((current) => {
      if (!current) return current;
      const scales = current.scales.map((scale, index) => {
        if (index !== scaleIndex) return scale;
        const items = scale.items.map((item, j) => {
          if (j !== itemIndex) return item;
          const options = item.options.map((option, k) =>
            k === optionIndex ? { ...option, label } : option,
          );
          return { ...item, options };
        });
        return { ...scale, items };
      });
      return { ...current, scales };
    });
  }

  function addScale() {
    setDetail((current) => (current ? { ...current, scales: [...current.scales, emptyScale(current.scales.length + 1)] } : current));
  }

  function removeScale(index: number) {
    setDetail((current) => {
      if (!current) return current;
      const scales = current.scales
        .filter((_, i) => i !== index)
        .map((scale, i) => ({ ...scale, display_order: i + 1 }));
      return { ...current, scales };
    });
  }

  function addItem(scaleIndex: number) {
    setDetail((current) => {
      if (!current) return current;
      const scales = current.scales.map((scale, index) => {
        if (index !== scaleIndex) return scale;
        const items = [
          ...scale.items,
          {
            item_order: scale.items.length + 1,
            text: "",
            locale: "es",
            required: true,
            options: NEUTRAL_OPTIONS.map((label, i) => ({ display_order: i + 1, label, locale: "es" })),
          },
        ];
        return { ...scale, items };
      });
      return { ...current, scales };
    });
  }

  function removeItem(scaleIndex: number, itemIndex: number) {
    setDetail((current) => {
      if (!current) return current;
      const scales = current.scales.map((scale, index) => {
        if (index !== scaleIndex) return scale;
        const items = scale.items
          .filter((_, i) => i !== itemIndex)
          .map((item, i) => ({ ...item, item_order: i + 1 }));
        return { ...scale, items };
      });
      return { ...current, scales };
    });
  }

  function validate(): string | null {
    if (!detail) return "No hay contenido cargado.";
    if (detail.scales.length === 0) return "Agregue al menos una escala.";
    for (const scale of detail.scales) {
      if (!scale.label.trim()) return "Toda escala necesita un nombre.";
      if (scale.items.length === 0) return `La escala «${scale.label}» necesita al menos un ítem.`;
      for (const item of scale.items) {
        if (!item.text.trim()) return `La escala «${scale.label}» tiene un ítem sin texto.`;
        if (item.options.length !== OPTION_COUNT) {
          return `El ítem «${item.text}» debe tener exactamente ${OPTION_COUNT} opciones.`;
        }
        for (const option of item.options) {
          if (!option.label.trim()) return `El ítem «${item.text}» tiene una opción sin etiqueta.`;
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
      await apiFetch(`/api/v1/catalog/admin/versions/${params.versionId}/content`, {
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
      });
      setNotice("Borrador guardado correctamente.");
    } catch (err) {
      const apiError = err instanceof ApiError ? err.payload : null;
      setError(
        apiError
          ? `${apiError.message}${apiError.request_id ? ` (ID: ${apiError.request_id})` : ""}`
          : "No se pudo guardar el borrador.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function publish() {
    if (busy || !detail) return;
    const validation = validate();
    if (validation) {
      setError(validation);
      return;
    }
    if (!window.confirm("Publicar versión congela el contenido: ya no se podrá editar. ¿Confirmar publicación?")) {
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await apiFetch(`/api/v1/catalog/admin/versions/${params.versionId}/publish`, {
        method: "POST",
        token: localStorage.getItem("psico_token") ?? "",
        idempotencyKey: crypto.randomUUID(),
      });
      setNotice("Versión publicada. La publicación es inmutable.");
      const refreshed = await apiFetch<AdminVersionDetail>(
        `/api/v1/catalog/admin/versions/${params.versionId}`,
        { token: localStorage.getItem("psico_token") ?? "" },
      );
      setDetail(refreshed);
    } catch (err) {
      const apiError = err instanceof ApiError ? err.payload : null;
      setError(
        apiError
          ? `${apiError.message}${apiError.request_id ? ` (ID: ${apiError.request_id})` : ""}`
          : "No se pudo publicar la versión.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function archive() {
    if (busy || !detail) return;
    if (!window.confirm("Archivar conserva el historial de referencias. ¿Confirmar archivo?")) {
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await apiFetch(`/api/v1/catalog/admin/versions/${params.versionId}/archive`, {
        method: "POST",
        token: localStorage.getItem("psico_token") ?? "",
        idempotencyKey: crypto.randomUUID(),
      });
      setNotice("Versión archivada.");
      const refreshed = await apiFetch<AdminVersionDetail>(
        `/api/v1/catalog/admin/versions/${params.versionId}`,
        { token: localStorage.getItem("psico_token") ?? "" },
      );
      setDetail(refreshed);
    } catch (err) {
      const apiError = err instanceof ApiError ? err.payload : null;
      setError(
        apiError
          ? `${apiError.message}${apiError.request_id ? ` (ID: ${apiError.request_id})` : ""}`
          : "No se pudo archivar la versión.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (error && !detail) {
    return (
      <main style={{ fontFamily: "system-ui, sans-serif", maxWidth: 720, margin: "2rem auto", padding: "0 1rem" }}>
        <h1>Catálogo de instrumentos</h1>
        <p style={{ color: "#b3261e" }}>{error}</p>
        <Link href="/catalogo">Volver al catálogo</Link>
      </main>
    );
  }

  if (!detail) {
    return <p style={{ fontFamily: "system-ui, sans-serif", padding: "2rem" }}>Cargando…</p>;
  }

  const statusLabel =
    detail.status === "draft" ? "Borrador" : detail.status === "published" ? "Versión publicada" : "Versión archivada";

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", maxWidth: 900, margin: "2rem auto", padding: "0 1rem" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
        <div>
          <h1 style={{ marginBottom: "0.25rem" }}>
            {detail.title} <span style={{ color: "#666", fontWeight: "normal" }}>({detail.instrument_key})</span>
          </h1>
          <p style={{ margin: 0, color: "#666" }}>
            v{detail.version_no} · {statusLabel}
            {detail.source === "seed" ? (
              <span title="Instrumento de referencia (sintético)" style={{ marginLeft: "0.5rem", color: "#8a5a00" }}>
                · referencia · solo lectura
              </span>
            ) : null}
            {detail.published_at ? ` · publicada el ${new Date(detail.published_at).toLocaleString("es-ES")}` : null}
          </p>
        </div>
        <Link href="/catalogo">← Volver al catálogo</Link>
      </header>

      {readOnly ? (
        <p style={{ color: "#8a5a00" }}>
          {detail.source === "seed"
            ? "Este instrumento es de referencia y no se puede editar."
            : "La versión publicada es inmutable."}
        </p>
      ) : null}
      {error ? <p style={{ color: "#b3261e" }}>{error}</p> : null}
      {notice ? <p style={{ color: "#1e8e3e" }}>{notice}</p> : null}

      <section style={{ marginTop: "1.5rem" }}>
        <h2>Escalas</h2>
        {detail.scales.map((scale, scaleIndex) => (
          <fieldset key={scale.id ?? `scale-${scaleIndex}`} style={{ marginBottom: "1rem", padding: "1rem" }}>
            <legend style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <span>Escala {scale.display_order}</span>
              {!readOnly ? (
                <button type="button" onClick={() => removeScale(scaleIndex)} style={{ cursor: "pointer", fontSize: "0.8rem" }}>
                  Quitar escala
                </button>
              ) : null}
            </legend>
            <label style={{ display: "block", marginBottom: "0.5rem" }}>
              Nombre
              <input
                type="text"
                value={scale.label}
                onChange={(event) => updateScale(scaleIndex, { label: event.target.value })}
                disabled={readOnly}
                style={{ display: "block", width: "100%", padding: "0.4rem" }}
              />
            </label>
            {scale.items.map((item, itemIndex) => (
              <fieldset key={item.id ?? `item-${scaleIndex}-${itemIndex}`} style={{ marginBottom: "0.75rem", padding: "0.75rem" }}>
                <legend style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  <span>Ítem {item.item_order}</span>
                  {!readOnly ? (
                    <button type="button" onClick={() => removeItem(scaleIndex, itemIndex)} style={{ cursor: "pointer", fontSize: "0.8rem" }}>
                      Quitar ítem
                    </button>
                  ) : null}
                </legend>
                <label style={{ display: "block", marginBottom: "0.5rem" }}>
                  Texto
                  <input
                    type="text"
                    value={item.text}
                    onChange={(event) => updateItem(scaleIndex, itemIndex, { text: event.target.value })}
                    disabled={readOnly}
                    style={{ display: "block", width: "100%", padding: "0.4rem" }}
                  />
                </label>
                <label style={{ display: "flex", gap: "0.4rem", alignItems: "center", marginBottom: "0.5rem" }}>
                  <input
                    type="checkbox"
                    checked={item.required}
                    onChange={(event) => updateItem(scaleIndex, itemIndex, { required: event.target.checked })}
                    disabled={readOnly}
                  />
                  Obligatorio
                </label>
                <div>
                  <span style={{ fontSize: "0.85rem", color: "#666" }}>Opciones de respuesta (1–5)</span>
                  {item.options.map((option, optionIndex) => (
                    <label key={option.id ?? `opt-${scaleIndex}-${itemIndex}-${optionIndex}`} style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginTop: "0.25rem" }}>
                      <span style={{ minWidth: "1.2rem" }}>{option.display_order}.</span>
                      <input
                        type="text"
                        value={option.label}
                        onChange={(event) => updateOption(scaleIndex, itemIndex, optionIndex, event.target.value)}
                        disabled={readOnly}
                        style={{ flex: 1, padding: "0.3rem" }}
                      />
                    </label>
                  ))}
                </div>
              </fieldset>
            ))}
            {!readOnly ? (
              <button type="button" onClick={() => addItem(scaleIndex)} style={{ cursor: "pointer" }}>
                + Agregar ítem
              </button>
            ) : null}
          </fieldset>
        ))}
        {!readOnly ? (
          <button type="button" onClick={addScale} style={{ cursor: "pointer" }}>
            + Agregar escala
          </button>
        ) : null}
      </section>

      <section style={{ marginTop: "1.5rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        {!readOnly ? (
          <button onClick={saveDraft} disabled={busy} style={{ padding: "0.6rem", cursor: "pointer" }}>
            {busy ? "Guardando…" : "Guardar borrador"}
          </button>
        ) : null}
        {canPublish ? (
          <button onClick={publish} disabled={busy} style={{ padding: "0.6rem", cursor: "pointer" }}>
            {busy ? "Publicando…" : "Publicar versión"}
          </button>
        ) : null}
        {canArchive ? (
          <button onClick={archive} disabled={busy} style={{ padding: "0.6rem", cursor: "pointer" }}>
            {busy ? "Archivando…" : "Archivar versión"}
          </button>
        ) : null}
        {detail.status === "published" ? (
          <Link href={`/catalogo/${params.instrumentId}/versiones/${params.versionId}/vista`} style={{ alignSelf: "center" }}>
            Ver vista del evaluado
          </Link>
        ) : null}
      </section>
    </main>
  );
}
