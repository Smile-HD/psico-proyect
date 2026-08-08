import type { ButtonHTMLAttributes, ReactNode } from "react";

import styles from "./Button.module.css";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "compact" | "default";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
	variant?: ButtonVariant;
	size?: ButtonSize;
	busy?: boolean;
	pendingLabel?: ReactNode;
	leadingIcon?: ReactNode;
	trailingIcon?: ReactNode;
};

export default function Button({
	variant = "primary",
	size = "default",
	busy = false,
	pendingLabel,
	leadingIcon,
	trailingIcon,
	children,
	disabled,
	className,
	...buttonProps
}: ButtonProps) {
	const rootClassName = [styles.root, className].filter(Boolean).join(" ");
	const visibleContent = busy && pendingLabel !== undefined ? pendingLabel : children;

	return (
		<button
			{...buttonProps}
			className={rootClassName}
			data-variant={variant}
			data-size={size}
			data-busy={busy || undefined}
			disabled={disabled || busy}
			aria-busy={busy ? "true" : buttonProps["aria-busy"]}
		>
			{leadingIcon ? (
				<span className={styles.icon} aria-hidden="true">
					{leadingIcon}
				</span>
			) : null}
			<span className={styles.content}>{visibleContent}</span>
			{trailingIcon ? (
				<span className={styles.icon} aria-hidden="true">
					{trailingIcon}
				</span>
			) : null}
		</button>
	);
}
