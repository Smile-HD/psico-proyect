import { useId, type ReactNode } from "react";

import Button from "./Button";
import styles from "./Feedback.module.css";

export type ErrorStateProps = {
	title?: string;
	message: string;
	retryLabel?: string;
	onRetry?: () => void;
	backAction?: ReactNode;
	className?: string;
};

export function ErrorState({
	title = "No se pudo completar la solicitud",
	message,
	retryLabel = "Reintentar",
	onRetry,
	backAction,
	className,
}: ErrorStateProps) {
	const titleId = `error-title-${useId()}`;
	const rootClassName = [styles.root, styles.errorState, className]
		.filter(Boolean)
		.join(" ");

	return (
		<section className={rootClassName} role="alert" aria-labelledby={titleId}>
			<div className={styles.marker} aria-hidden="true">
				!
			</div>
			<div className={styles.content}>
				<h2 id={titleId}>{title}</h2>
				<p>{message}</p>
				{onRetry || backAction ? (
					<div className={styles.actions}>
						{onRetry ? (
							<Button type="button" variant="secondary" onClick={onRetry}>
								{retryLabel}
							</Button>
						) : null}
						{backAction}
					</div>
				) : null}
			</div>
		</section>
	);
}

export type NoticeTone = "success" | "info" | "warning" | "error";

export type NoticeProps = {
	tone: NoticeTone;
	message: string;
	title?: string;
	role?: "status" | "alert";
	className?: string;
};

export function Notice({ tone, message, title, role, className }: NoticeProps) {
	const resolvedRole = role ?? (tone === "error" ? "alert" : "status");
	const rootClassName = [styles.root, styles.notice, className]
		.filter(Boolean)
		.join(" ");

	return (
		<div
			className={rootClassName}
			data-tone={tone}
			role={resolvedRole}
			aria-live={resolvedRole === "status" ? "polite" : undefined}
		>
			<div className={styles.marker} aria-hidden="true">
				{tone === "error" ? "!" : "·"}
			</div>
			<div className={styles.content}>
				{title ? <h2>{title}</h2> : null}
				<p>{message}</p>
			</div>
		</div>
	);
}
