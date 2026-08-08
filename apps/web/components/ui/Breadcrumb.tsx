import Link from "next/link";
import type { ReactNode } from "react";

import styles from "./Breadcrumb.module.css";

export type BreadcrumbItem = {
	label: string;
	href?: string;
	current?: boolean;
};

export type BreadcrumbProps = {
	items: readonly BreadcrumbItem[];
	className?: string;
};

export default function Breadcrumb({ items, className }: BreadcrumbProps) {
	const rootClassName = [styles.root, className].filter(Boolean).join(" ");
	const lastIndex = items.length - 1;

	return (
		<nav className={rootClassName} aria-label="Ruta de navegación">
			<ol>
				{items.map((item, index) => {
					const isCurrent = index === lastIndex;
					const content: ReactNode = isCurrent ? (
						<span aria-current="page">{item.label}</span>
					) : item.href ? (
						<Link href={item.href}>{item.label}</Link>
					) : (
						<span>{item.label}</span>
					);

					return (
						<li key={`${item.label}-${index}`}>
							{content}
							{index < lastIndex ? (
								<span className={styles.separator} aria-hidden="true">
									→
								</span>
							) : null}
						</li>
					);
				})}
			</ol>
		</nav>
	);
}
