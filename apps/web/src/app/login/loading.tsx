import Skeleton from "@/components/ui/Skeleton";
import styles from "../loading.module.css";

/** TestPsico — login form loading surface. */
export default function LoginLoading() {
	return (
		<main id="main-content" className={styles.root}>
			<Skeleton variant="heading" />
			<Skeleton variant="control" />
			<Skeleton variant="control" />
			<Skeleton variant="control" />
		</main>
	);
}
