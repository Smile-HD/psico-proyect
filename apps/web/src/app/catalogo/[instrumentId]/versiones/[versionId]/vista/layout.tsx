import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "Vista del instrumento",
	description:
		"Consulta una versión publicada del instrumento en modo de investigación.",
};

export default function PreviewLayout({
	children,
}: {
	children: React.ReactNode;
}) {
	return children;
}
