import type { CSSProperties } from "react";

import styles from "./Skeleton.module.css";

export type SkeletonVariant = "text" | "heading" | "control" | "block" | "table";

export type SkeletonProps = {
	variant: SkeletonVariant;
	lines?: number;
	rows?: number;
	columns?: number;
	label?: string;
	className?: string;
};

export default function Skeleton({
	variant,
	lines = 3,
	rows = 4,
	columns = 5,
	label = "Cargando…",
	className,
}: SkeletonProps) {
	const rootClassName = [styles.root, className].filter(Boolean).join(" ");
	const safeLines = Math.max(1, lines);
	const safeRows = Math.max(1, rows);
	const safeColumns = Math.max(1, columns);

	return (
		<div className={rootClassName} data-variant={variant} role="status" aria-live="polite">
			<span className={styles.visuallyHidden}>{label}</span>
			{variant === "table" ? (
				<div
					className={styles.tableGrid}
					style={{ "--skeleton-columns": safeColumns } as CSSProperties}
					aria-hidden="true"
				>
					{Array.from({ length: safeColumns }, (_, index) => (
						<span className={styles.tableHeader} key={`header-${index}`} />
					))}
					{Array.from({ length: safeRows * safeColumns }, (_, index) => (
						<span className={styles.tableCell} key={`cell-${index}`} />
					))}
				</div>
			) : (
				<div className={styles.stack} aria-hidden="true">
					{Array.from(
						{ length: variant === "block" || variant === "control" ? 1 : safeLines },
						(_, index) => <span className={styles.shape} key={index} />,
					)}
				</div>
			)}
		</div>
	);
}
