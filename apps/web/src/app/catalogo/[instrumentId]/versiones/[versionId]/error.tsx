"use client";

import Link from "next/link";
import { ErrorState } from "@/components/ui/Feedback";
import styles from "../../../../error.module.css";

/** TestPsico — version editor route error boundary. */
export default function VersionError({
	reset,
}: {
	error: Error & { digest?: string };
	reset: () => void;
}) {
	return (
		<main id="main-content" className={styles.root}>
			<ErrorState
				title="No se pudo cargar la versión"
				message="Ocurrió un error inesperado. Podés reintentar o volver al catálogo."
				retryLabel="Reintentar"
				onRetry={reset}
				backAction={
					<Link href="/catalogo" className={styles.backLink}>
						Volver al catálogo
					</Link>
				}
			/>
		</main>
	);
}
