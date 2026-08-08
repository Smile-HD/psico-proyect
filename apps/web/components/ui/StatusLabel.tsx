import type { ReactNode } from "react";

import styles from "./StatusLabel.module.css";

export type StatusKind =
	| "draft"
	| "published"
	| "archived"
	| "reference"
	| "success"
	| "warning"
	| "error"
	| "neutral";

export type StatusLabelProps = {
	kind: StatusKind;
	children: ReactNode;
	symbol?: ReactNode;
	className?: string;
};

export default function StatusLabel({
	kind,
	children,
	symbol,
	className,
}: StatusLabelProps) {
	const rootClassName = [styles.root, className].filter(Boolean).join(" ");

	return (
		<span className={rootClassName} data-kind={kind}>
			{symbol ? (
				<span className={styles.symbol} aria-hidden="true">
					{symbol}
				</span>
			) : null}
			<span>{children}</span>
		</span>
	);
}
