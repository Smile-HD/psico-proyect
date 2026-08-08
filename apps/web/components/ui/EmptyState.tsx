import { useId, type ReactNode } from "react";

import styles from "./EmptyState.module.css";

export type EmptyStateProps = {
	title: string;
	description: string;
	action?: ReactNode;
	contextLabel?: string;
	className?: string;
};

export default function EmptyState({
	title,
	description,
	action,
	contextLabel,
	className,
}: EmptyStateProps) {
	const titleId = `empty-state-title-${useId()}`;
	const rootClassName = [styles.root, className].filter(Boolean).join(" ");

	return (
		<section className={rootClassName} aria-labelledby={titleId}>
			{contextLabel ? (
				<p className={styles.contextLabel}>{contextLabel}</p>
			) : null}
			<h2 id={titleId}>{title}</h2>
			<p className={styles.description}>{description}</p>
			{action ? <div className={styles.action}>{action}</div> : null}
		</section>
	);
}
