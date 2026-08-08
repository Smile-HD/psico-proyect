import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "TestPsico — Estado del servicio",
  description: "Página de estado del servicio de TestPsico (entorno de desarrollo con datos sintéticos)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <nav style={{ fontFamily: "system-ui, sans-serif", padding: "0.5rem 1rem", borderBottom: "1px solid #eee" }}>
          <Link href="/" style={{ marginRight: "1rem" }}>
            Estado del servicio
          </Link>
          <Link href="/catalogo">Catálogo de instrumentos</Link>
        </nav>
        {children}
      </body>
    </html>
  );
}
