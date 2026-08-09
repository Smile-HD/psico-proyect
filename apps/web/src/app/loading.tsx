import Skeleton from "@/components/ui/Skeleton";
import styles from "./loading.module.css";

/**
 * TestPsico — branded root loading fallback.
 *
 * Reserved shell space so the page never jumps when data arrives.
 */
export default function RootLoading() {
	return (
		<main id="main-content" className={styles.root}>
			<Skeleton variant="heading" />
			<Skeleton variant="text" />
			<Skeleton variant="text" />
			<Skeleton variant="control" />
		</main>
	);
}
