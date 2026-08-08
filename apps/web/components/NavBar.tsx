"use client";

import Link from "next/link";
import { getSessionUser } from "@/lib/auth";

/**
 * TestPsico — top navigation.
 *
 * Client component because it reads the session from localStorage. The catalog
 * link is only shown to admin/psicologo (design F2: evaluado sees no admin
 * navigation). The server remains the authority for every permission decision.
 */
export default function NavBar() {
	const user = getSessionUser();
	const canManage =
		user?.roles.includes("admin") || user?.roles.includes("psicologo");

	return (
		<nav
			style={{
				fontFamily: "system-ui, sans-serif",
				padding: "0.5rem 1rem",
				borderBottom: "1px solid #eee",
			}}
		>
			<Link href="/" style={{ marginRight: "1rem" }}>
				Estado del servicio
			</Link>
			{canManage ? (
				<Link href="/catalogo">Catálogo de instrumentos</Link>
			) : null}
			{user ? (
				<span style={{ marginLeft: "1rem", color: "#666" }}>
					{user.username}
				</span>
			) : (
				<Link href="/login" style={{ marginLeft: "1rem" }}>
					Iniciar sesión
				</Link>
			)}
		</nav>
	);
}
