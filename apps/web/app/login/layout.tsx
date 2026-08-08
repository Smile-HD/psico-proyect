import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Iniciar sesión",
  description: "Acceso al espacio de trabajo de TestPsico.",
};

export default function LoginLayout({ children }: { children: React.ReactNode }) {
  return children;
}
