import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Catálogo de instrumentos",
  description: "Consulta y administra instrumentos psicotécnicos sintéticos.",
};

export default function CatalogLayout({ children }: { children: React.ReactNode }) {
  return children;
}
