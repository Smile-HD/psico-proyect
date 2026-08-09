"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { clearSession, useSessionUser } from "@/lib/auth";
import styles from "./NavBar.module.css";

export type NavBarProps = {
	className?: string;
	onLogout?: () => void;
};

/** Short display label for each role — keeps the UI in Spanish per spec. */
function roleLabel(roles: string[]): string {
	if (roles.includes("admin")) return "admin";
	if (roles.includes("psicólogo")) return "psicólogo";
	if (roles.includes("evaluado")) return "evaluado";
	return roles[0] ?? "";
}

export default function NavBar({ className, onLogout }: NavBarProps) {
	const router = useRouter();
	const pathname = usePathname() ?? "";
	const { user, ready } = useSessionUser();
	const [menuOpen, setMenuOpen] = useState(false);

	const canManage =
		ready &&
		(user?.roles.includes("admin") || user?.roles.includes("psicólogo"));
	const isEvaluado = ready && user?.roles.includes("evaluado");

	const isHomeActive = pathname === "/";
	const isCatalogActive =
		pathname === "/catalogo" || pathname.startsWith("/catalogo/");
	const isSessionActive =
		pathname === "/sesion" || pathname.startsWith("/sesion");

	useEffect(() => {
		setMenuOpen(false);
	}, [pathname]);

	function handleLogout() {
		if (onLogout) {
			onLogout();
			return;
		}
		clearSession();
		router.replace("/login");
	}

	const rootClassName = [styles.root, className].filter(Boolean).join(" ");
	const navClassName = [styles.nav, menuOpen ? styles.navOpen : ""]
		.filter(Boolean)
		.join(" ");

	return (
		<header className={rootClassName}>
			<div className={styles.inner}>
				<Link
					className={styles.brand}
					href="/"
					aria-label="Ir al inicio de TestPsico"
				>
					TestPsico
				</Link>

				<button
					className={styles.menuToggle}
					type="button"
					aria-label={
						menuOpen ? "Cerrar menú de navegación" : "Abrir menú de navegación"
					}
					aria-expanded={menuOpen}
					aria-controls="primary-navigation"
					data-open={menuOpen}
					onClick={() => setMenuOpen((open) => !open)}
				>
					<span className={styles.toggleIcon} aria-hidden="true">
						<span className={`${styles.toggleLine} ${styles.toggleLineTop}`} />
						<span
							className={`${styles.toggleLine} ${styles.toggleLineBottom}`}
						/>
					</span>
				</button>

				<nav
					id="primary-navigation"
					className={navClassName}
					aria-label="Navegación principal"
				>
					<ul className={styles.navList}>
						<li>
							<Link
								className={styles.navLink}
								href="/"
								aria-current={isHomeActive ? "page" : undefined}
							>
								Estado del servicio
							</Link>
						</li>
						{canManage ? (
							<li>
								<Link
									className={styles.navLink}
									href="/catalogo"
									aria-current={isCatalogActive ? "page" : undefined}
								>
									Catálogo de instrumentos
								</Link>
							</li>
						) : null}
						{isEvaluado ? (
							<li>
								<Link
									className={styles.navLink}
									href="/sesion"
									aria-current={isSessionActive ? "page" : undefined}
								>
									Rendir test
								</Link>
							</li>
						) : null}
					</ul>
				</nav>

				{ready ? (
					<div className={styles.userArea}>
						{user ? (
							<>
								<span className={styles.username}>
									{user.username}
									{user.roles.length > 0 ? (
										<span className={styles.roleChip}>
											{roleLabel(user.roles)}
										</span>
									) : null}
								</span>
								<button
									className={styles.authButton}
									type="button"
									onClick={handleLogout}
								>
									Salir
								</button>
							</>
						) : (
							<Link className={styles.authButton} href="/login">
								Iniciar sesión
							</Link>
						)}
					</div>
				) : null}
			</div>
		</header>
	);
}
