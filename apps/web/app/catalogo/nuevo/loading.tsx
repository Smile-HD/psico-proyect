import Skeleton from "@/components/ui/Skeleton";
import styles from "../../loading.module.css";

/** TestPsico — new instrument form loading surface. */
export default function NuevoLoading() {
	return (
		<main id="main-content" className={styles.root}>
			<Skeleton variant="heading" />
			<Skeleton variant="control" />
			<Skeleton variant="control" />
			<Skeleton variant="control" />
		</main>
	);
}
