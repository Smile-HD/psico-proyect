"use client";

import { ErrorState } from "@/components/ui/Feedback";
import styles from "./error.module.css";

/**
 * TestPsico — root client error boundary.
 *
 * Catches render errors on client routes and offers a working retry via
 * Next.js `reset()`. Never prints raw exceptions or envelopes.
 */
export default function RootError({
	error,
	reset,
}: {
	error: Error & { digest?: string };
	reset: () => void;
}) {
	return (
		<main id="main-content" className={styles.root}>
			<ErrorState
				title="Ocurrió un error inesperado"
				message="No se pudo mostrar esta página. Podés reintentar o volver al inicio."
				retryLabel="Reintentar"
				onRetry={reset}
			/>
			{error.digest ? (
				<p className={styles.digest}>Referencia: {error.digest}</p>
			) : null}
		</main>
	);
}
