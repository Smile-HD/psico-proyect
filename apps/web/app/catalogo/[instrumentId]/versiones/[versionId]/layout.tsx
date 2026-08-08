import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Editor de versión",
  description: "Edita una versión de instrumento dentro del catálogo de investigación.",
};

export default function VersionLayout({ children }: { children: React.ReactNode }) {
  return children;
}
