import Button from "./Button";
import styles from "./Pagination.module.css";

export type PaginationProps = {
	page: number;
	pageSize: number;
	total: number;
	onPageChange: (page: number) => void;
	ariaLabel?: string;
	className?: string;
};

export default function Pagination({
	page,
	pageSize,
	total,
	onPageChange,
	ariaLabel = "Paginación del catálogo",
	className,
}: PaginationProps) {
	const safePageSize = Math.max(1, pageSize);
	const totalPages = Math.max(1, Math.ceil(Math.max(0, total) / safePageSize));
	const currentPage = Math.min(Math.max(1, page), totalPages);
	const rootClassName = [styles.root, className].filter(Boolean).join(" ");
	const changePage = (nextPage: number) => {
		onPageChange(Math.min(Math.max(1, nextPage), totalPages));
	};

	return (
		<nav className={rootClassName} aria-label={ariaLabel}>
			<Button
				variant="secondary"
				size="compact"
				type="button"
				disabled={currentPage === 1}
				onClick={() => changePage(currentPage - 1)}
			>
				Anterior
			</Button>
			{totalPages > 1 ? (
				<div className={styles.pages} aria-label="Páginas">
					{Array.from({ length: totalPages }, (_, index) => {
						const pageNumber = index + 1;
						const isCurrent = pageNumber === currentPage;

						return (
							<Button
								key={pageNumber}
								variant={isCurrent ? "primary" : "ghost"}
								size="compact"
								type="button"
								aria-current={isCurrent ? "page" : undefined}
								aria-label={`Ir a la página ${pageNumber}`}
								onClick={() => changePage(pageNumber)}
							>
								{isCurrent
									? `Página ${pageNumber} de ${totalPages}`
									: pageNumber}
							</Button>
						);
					})}
				</div>
			) : (
				<span className={styles.currentPage} aria-current="page">
					Página 1 de 1
				</span>
			)}
			<Button
				variant="secondary"
				size="compact"
				type="button"
				disabled={currentPage === totalPages}
				onClick={() => changePage(currentPage + 1)}
			>
				Siguiente
			</Button>
		</nav>
	);
}
