import type { ReactNode } from "react";

import styles from "./Table.module.css";

export type TableColumn<Row> = {
	id: string;
	header: ReactNode;
	render: (row: Row) => ReactNode;
	numeric?: boolean;
	rowHeader?: boolean;
};

export type TableProps<Row> = {
	caption: string;
	captionHidden?: boolean;
	columns: readonly TableColumn<Row>[];
	rows: readonly Row[];
	rowKey: (row: Row) => string;
	className?: string;
};

export default function Table<Row>({
	caption,
	captionHidden = false,
	columns,
	rows,
	rowKey,
	className,
}: TableProps<Row>) {
	const scrollClassName = [styles.scrollRegion, className]
		.filter(Boolean)
		.join(" ");

	return (
		<div
			className={scrollClassName}
			role="region"
			aria-label={caption}
			tabIndex={0}
		>
			<table className={styles.table}>
				<caption
					className={captionHidden ? styles.visuallyHidden : styles.caption}
				>
					{caption}
				</caption>
				<thead>
					<tr>
						{columns.map((column) => (
							<th
								key={column.id}
								scope="col"
								className={column.numeric ? styles.numeric : undefined}
							>
								{column.header}
							</th>
						))}
					</tr>
				</thead>
				<tbody>
					{rows.map((row) => (
						<tr key={rowKey(row)}>
							{columns.map((column) => {
								const cellClassName = column.numeric
									? styles.numeric
									: undefined;
								const content = column.render(row);

								return column.rowHeader ? (
									<th key={column.id} scope="row" className={cellClassName}>
										{content}
									</th>
								) : (
									<td key={column.id} className={cellClassName}>
										{content}
									</td>
								);
							})}
						</tr>
					))}
				</tbody>
			</table>
		</div>
	);
}
