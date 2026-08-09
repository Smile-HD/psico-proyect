import Skeleton from "@/components/ui/Skeleton";
import styles from "../../../../../loading.module.css";

/** TestPsico — evaluator view loading surface (matches matrix layout). */
export default function VistaLoading() {
	return (
		<main id="main-content" className={styles.root}>
			<Skeleton variant="heading" />
			<Skeleton variant="table" />
		</main>
	);
}
