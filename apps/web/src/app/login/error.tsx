"use client";

import Link from "next/link";
import { ErrorState } from "@/components/ui/Feedback";
import styles from "../error.module.css";

/** TestPsico — login route error boundary. */
export default function LoginError({
	reset,
}: {
	error: Error & { digest?: string };
	reset: () => void;
}) {
	return (
		<main id="main-content" className={styles.root}>
			<ErrorState
				title="No se pudo mostrar el inicio de sesión"
				message="Ocurrió un error inesperado. Podés reintentar o volver al inicio."
				retryLabel="Reintentar"
				onRetry={reset}
				backAction={
					<Link href="/" className={styles.backLink}>
						Volver al inicio
					</Link>
				}
			/>
		</main>
	);
}
