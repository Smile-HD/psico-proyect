import { useId, type ChangeEvent } from "react";

import styles from "./LikertMatrix.module.css";

export type LikertOption = {
	id: string;
	order: number;
	label: string;
};

export type LikertItem = {
	id: string;
	order: number;
	text: string;
	required: boolean;
	options: readonly LikertOption[];
};

export type LikertMatrixProps = {
	caption: string;
	items: readonly LikertItem[];
	interactive?: boolean;
	valueByItem?: Readonly<Record<string, string>>;
	onChange?: (itemId: string, optionId: string) => void;
	className?: string;
};

export default function LikertMatrix({
	caption,
	items,
	interactive = false,
	valueByItem = {},
	onChange,
	className,
}: LikertMatrixProps) {
	const matrixId = `likert-${useId().replace(/:/g, "")}`;
	const columnOptions = items[0]?.options ?? [];
	const rootClassName = [styles.scrollRegion, className]
		.filter(Boolean)
		.join(" ");

	function handleChange(
		event: ChangeEvent<HTMLInputElement>,
		itemId: string,
		optionId: string,
	) {
		if (event.target.checked) onChange?.(itemId, optionId);
	}

	return (
		<div
			className={rootClassName}
			role="region"
			aria-label={caption}
			tabIndex={0}
		>
			<table className={styles.table}>
				<caption>{caption}</caption>
				<thead>
					<tr>
						<th id={`${matrixId}-item-heading`} scope="col">
							Ítem
						</th>
						{columnOptions.map((option, optionIndex) => (
							<th
								id={`${matrixId}-option-${optionIndex}`}
								key={`${option.id}-${optionIndex}`}
								scope="col"
							>
								{option.label}
							</th>
						))}
					</tr>
				</thead>
				<tbody>
					{items.map((item, itemIndex) => {
						const rowHeaderId = `${matrixId}-item-${itemIndex}`;
						return (
							<tr key={item.id}>
								<th id={rowHeaderId} scope="row">
									<span>{item.text}</span>
									{item.required ? (
										<span className={styles.required}> (obligatorio)</span>
									) : null}
								</th>
								{columnOptions.map((columnOption, optionIndex) => {
									const option = item.options[optionIndex] ?? columnOption;
									const optionHeaderId = `${matrixId}-option-${optionIndex}`;
									const checked = valueByItem[item.id] === option.id;
									return (
										<td
											key={`${item.id}-${option.id}`}
											headers={`${rowHeaderId} ${optionHeaderId}`}
										>
											{interactive && onChange ? (
												<input
													type="radio"
													name={`${matrixId}-item-${item.id}`}
													value={option.id}
													checked={checked}
													aria-label={`${item.text}: ${option.label}`}
													onChange={(event) =>
														handleChange(event, item.id, option.id)
													}
												/>
											) : (
												<span className={styles.cellMark} aria-hidden="true">
													·
												</span>
											)}
										</td>
									);
								})}
							</tr>
						);
					})}
				</tbody>
			</table>
		</div>
	);
}
