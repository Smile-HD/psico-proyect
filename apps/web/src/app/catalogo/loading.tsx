import Skeleton from "@/components/ui/Skeleton";
import styles from "../loading.module.css";

/** TestPsico — catalog list loading surface (matches final table layout). */
export default function CatalogLoading() {
	return (
		<main id="main-content" className={styles.root}>
			<Skeleton variant="heading" />
			<Skeleton variant="table" />
		</main>
	);
}
