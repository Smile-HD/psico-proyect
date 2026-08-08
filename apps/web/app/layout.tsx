import type { Metadata } from "next";
import NavBar from "@/components/NavBar";
import "./globals.css";

export const metadata: Metadata = {
	title: "TestPsico — Estado del servicio",
	description:
		"Página de estado del servicio de TestPsico (entorno de desarrollo con datos sintéticos)",
};

export default function RootLayout({
	children,
}: {
	children: React.ReactNode;
}) {
	return (
		<html lang="es">
			<body>
				<NavBar />
				{children}
			</body>
		</html>
	);
}
