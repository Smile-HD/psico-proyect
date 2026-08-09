import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "Nuevo instrumento",
	description:
		"Registra un instrumento sintético para el catálogo de investigación.",
};

export default function NewInstrumentLayout({
	children,
}: {
	children: React.ReactNode;
}) {
	return children;
}
