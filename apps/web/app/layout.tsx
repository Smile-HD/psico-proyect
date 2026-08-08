import localFont from "next/font/local";
import type { Metadata, Viewport } from "next";
import NavBar from "@/components/NavBar";
import styles from "./layout.module.css";
import "./globals.css";

const sourceSans3 = localFont({
	src: "./fonts/SourceSans3-Variable.woff2",
	display: "swap",
	weight: "400 700",
	style: "normal",
	variable: "--font-source-sans-3",
});

export const metadata: Metadata = {
	title: {
		default: "TestPsico",
		template: "%s | TestPsico",
	},
	description:
		"Herramienta de orientación psicotécnica para investigación con datos sintéticos.",
	icons: {
		icon: "/favicon.svg",
	},
};

export const viewport: Viewport = {
	width: "device-width",
	initialScale: 1,
	themeColor: "rgb(247 248 250)",
};

export default function RootLayout({
	children,
}: {
	children: React.ReactNode;
}) {
	return (
		<html lang="es">
			<body className={sourceSans3.variable}>
				<a className={styles.skipLink} href="#main-content">
					Saltar al contenido principal
				</a>
				<div id="app-shell" className={styles.shell}>
					<NavBar />
					<main id="main-content" className={styles.main} tabIndex={-1}>
						{children}
					</main>
					<footer className={styles.footer}>
						<div className={styles.footerContent}>
							<p className={styles.footerNote}>
								TestPsico · entorno de investigación
							</p>
							<p>
								Todos los datos son sintéticos y de uso exclusivo para
								investigación (research-only).
							</p>
						</div>
					</footer>
				</div>
			</body>
		</html>
	);
}
