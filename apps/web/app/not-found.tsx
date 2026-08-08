import Link from "next/link";
import styles from "./not-found.module.css";

/**
 * TestPsico — branded Spanish 404.
 */
export default function NotFound() {
	return (
		<main id="main-content" className={styles.root}>
			<p className={styles.code}>404</p>
			<h1>Página no encontrada</h1>
			<p>
				La dirección que buscás no existe o fue movida. Podés volver al inicio del
				servicio.
			</p>
			<Link className={styles.link} href="/">
				Volver al inicio
			</Link>
		</main>
	);
}
