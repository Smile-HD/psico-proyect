"use client";

import {
	useEffect,
	useId,
	useRef,
	useState,
	type ReactNode,
	type RefObject,
} from "react";
import { createPortal } from "react-dom";

import styles from "./Dialog.module.css";

const FOCUSABLE_SELECTOR = [
	"a[href]",
	"area[href]",
	"button:not([disabled])",
	"input:not([disabled]):not([type=hidden])",
	"select:not([disabled])",
	"textarea:not([disabled])",
	"iframe",
	"object",
	"embed",
	"[contenteditable]",
	"[tabindex]:not([tabindex='-1'])",
].join(",");

type InertElement = HTMLElement & { inert?: boolean };

function getFocusableElements(panel: HTMLElement): HTMLElement[] {
	return Array.from(
		panel.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
	).filter((element) => !element.hasAttribute("aria-hidden"));
}

export type DialogProps = {
	open: boolean;
	title: string;
	description: string;
	onClose: () => void;
	children: ReactNode;
	initialFocusRef?: RefObject<HTMLElement>;
	inertTargetId?: string;
	className?: string;
};

export default function Dialog({
	open,
	title,
	description,
	onClose,
	children,
	initialFocusRef,
	inertTargetId = "app-shell",
	className,
}: DialogProps) {
	const [mounted, setMounted] = useState(false);
	const panelRef = useRef<HTMLDivElement | null>(null);
	const returnFocusRef = useRef<HTMLElement | null>(null);
	const onCloseRef = useRef(onClose);
	onCloseRef.current = onClose;
	const ids = useId();
	const titleId = `dialog-title-${ids}`;
	const descriptionId = `dialog-description-${ids}`;

	useEffect(() => {
		setMounted(true);
	}, []);

	useEffect(() => {
		if (!mounted || !open) {
			return undefined;
		}

		const panel = panelRef.current;
		if (!panel) {
			return undefined;
		}

		returnFocusRef.current =
			document.activeElement instanceof HTMLElement
				? document.activeElement
				: null;

		const shell = document.getElementById(inertTargetId) as InertElement | null;
		const previousShellState = shell
			? {
					ariaHidden: shell.getAttribute("aria-hidden"),
					inert: "inert" in shell ? shell.inert : undefined,
					hadInertProperty: "inert" in shell,
				}
			: null;
		const previousBodyOverflow = document.body.style.overflow;

		document.body.style.overflow = "hidden";
		if (shell) {
			shell.setAttribute("aria-hidden", "true");
			if (previousShellState?.hadInertProperty) {
				shell.inert = true;
			}
		}

		const requestedFocus = initialFocusRef?.current;
		const focusTarget =
			requestedFocus && panel.contains(requestedFocus)
				? requestedFocus
				: (panel.querySelector<HTMLElement>("[data-dialog-autofocus]") ??
					panel.querySelector<HTMLElement>(
						"[data-dialog-cancel], button:not([data-dialog-confirm])",
					) ??
					getFocusableElements(panel)[0] ??
					panel);
		const focusFrame = window.requestAnimationFrame(() => {
			focusTarget.focus();
		});

		const handleKeyDown = (event: KeyboardEvent) => {
			if (event.key === "Escape") {
				event.preventDefault();
				onCloseRef.current();
				return;
			}
			if (event.key !== "Tab") {
				return;
			}

			const focusable = getFocusableElements(panel);
			if (focusable.length === 0) {
				event.preventDefault();
				panel.focus();
				return;
			}

			const first = focusable[0];
			const last = focusable[focusable.length - 1];
			const activeElement = document.activeElement;
			if (!panel.contains(activeElement)) {
				event.preventDefault();
				(event.shiftKey ? last : first).focus();
			} else if (event.shiftKey && activeElement === first) {
				event.preventDefault();
				last.focus();
			} else if (!event.shiftKey && activeElement === last) {
				event.preventDefault();
				first.focus();
			}
		};

		document.addEventListener("keydown", handleKeyDown);

		return () => {
			window.cancelAnimationFrame(focusFrame);
			document.removeEventListener("keydown", handleKeyDown);
			document.body.style.overflow = previousBodyOverflow;
			if (shell && previousShellState) {
				if (previousShellState.ariaHidden === null) {
					shell.removeAttribute("aria-hidden");
				} else {
					shell.setAttribute("aria-hidden", previousShellState.ariaHidden);
				}
				if (previousShellState.hadInertProperty) {
					shell.inert = Boolean(previousShellState.inert);
				}
			}
			const returnFocus = returnFocusRef.current;
			if (returnFocus?.isConnected && !returnFocus.hasAttribute("disabled")) {
				returnFocus.focus();
			}
			returnFocusRef.current = null;
		};
	}, [inertTargetId, mounted, open, initialFocusRef]);

	if (!mounted || !open) {
		return null;
	}

	const rootClassName = [styles.panel, className].filter(Boolean).join(" ");
	const dialog = (
		<div className={styles.overlay}>
			<div
				ref={panelRef}
				className={rootClassName}
				role="dialog"
				aria-modal="true"
				aria-labelledby={titleId}
				aria-describedby={descriptionId}
				tabIndex={-1}
			>
				<header className={styles.header}>
					<h2 id={titleId}>{title}</h2>
				</header>
				<p id={descriptionId} className={styles.description}>
					{description}
				</p>
				<div className={styles.actions}>{children}</div>
			</div>
		</div>
	);

	return createPortal(dialog, document.body);
}
