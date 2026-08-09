import Skeleton from "@/components/ui/Skeleton";
import styles from "../../../../loading.module.css";

/** TestPsico — version editor loading surface. */
export default function VersionLoading() {
	return (
		<main id="main-content" className={styles.root}>
			<Skeleton variant="heading" />
			<Skeleton variant="control" />
			<Skeleton variant="block" />
			<Skeleton variant="block" />
		</main>
	);
}
