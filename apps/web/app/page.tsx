import { unstable_noStore as noStore } from "next/cache";

/**
 * TestPsico — vertical slice (F1).
 *
 * Calls the API by its compose service name (`api`) over the internal network,
 * proving the compose wiring for later phases. UI texts are Spanish. If the
 * API is unreachable, a friendly Spanish error is shown — never a stack trace.
 */

type SeedStatus = {
  seed: {
    items: number;
    reference_sets: number;
    profiles: number;
    sessions: number;
    responses: number;
    consent_grants: number;
  };
  manifest: { seed_version: string; checksum: string; executed_at: string | null } | null;
};

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

export default async function Home() {
  noStore();

  const apiBase = process.env.API_BASE_URL ?? "http://api:8000";

  let health: { status?: string } | null = null;
  let seed: SeedStatus | null = null;
  let error: string | null = null;

  try {
    const [healthResult, seedResult] = await Promise.all([
      fetchJson<{ status?: string }>(`${apiBase}/health`),
      fetchJson<SeedStatus>(`${apiBase}/api/v1/seed/status`),
    ]);
    health = healthResult;
    seed = seedResult;
  } catch {
    error = "No se pudo conectar con el servicio de la API. Intente nuevamente más tarde.";
  }

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", maxWidth: 640, margin: "3rem auto", padding: "0 1rem" }}>
      <h1>TestPsico — Estado del servicio</h1>

      <section>
        <h2>Salud de la API</h2>
        {error ? (
          <p style={{ color: "#b3261e" }}>{error}</p>
        ) : health?.status === "ok" ? (
          <p style={{ color: "#1e8e3e" }}>OK</p>
        ) : (
          <p style={{ color: "#b3261e" }}>No disponible</p>
        )}
      </section>

      <section>
        <h2>Semilla (datos sintéticos)</h2>
        {error || !seed ? (
          <p>No hay información de la semilla disponible.</p>
        ) : (
          <>
            <ul>
              <li>Ítems: {seed.seed.items}</li>
              <li>Conjuntos de referencia: {seed.seed.reference_sets}</li>
              <li>Perfiles: {seed.seed.profiles}</li>
              <li>Sesiones: {seed.seed.sessions}</li>
              <li>Respuestas: {seed.seed.responses}</li>
              <li>Consentimientos: {seed.seed.consent_grants}</li>
            </ul>
            {seed.manifest ? (
              <p>
                Manifest: versión {seed.manifest.seed_version} · ejecutado el{" "}
                {new Date(seed.manifest.executed_at ?? "").toLocaleString("es-ES")}
              </p>
            ) : null}
          </>
        )}
      </section>

      <footer style={{ marginTop: "3rem", color: "#666" }}>
        Entorno de desarrollo. Todos los datos son sintéticos y de uso exclusivo
        para investigación (research-only).
      </footer>
    </main>
  );
}
