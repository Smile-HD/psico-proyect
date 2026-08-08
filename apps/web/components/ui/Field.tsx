"use client";

import {
	forwardRef,
	useImperativeHandle,
	useRef,
	type ChangeEventHandler,
	type FocusEventHandler,
	type ForwardedRef,
	type InputHTMLAttributes,
	type ReactNode,
} from "react";

import styles from "./Field.module.css";

export type FieldControl = "input" | "textarea" | "select" | "checkbox";

export type FieldOption = {
	value: string;
	label: string;
};

export type FieldControlHandle = {
	focus: () => void;
};

export type FieldProps = {
	id: string;
	name?: string;
	label: string;
	control?: FieldControl;
	type?: InputHTMLAttributes<HTMLInputElement>["type"];
	value?: string;
	checked?: boolean;
	onChange?: ChangeEventHandler<
		HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
	>;
	options?: readonly FieldOption[];
	helperText?: string;
	error?: string;
	required?: boolean;
	disabled?: boolean;
	readOnly?: boolean;
	placeholder?: string;
	autoComplete?: string;
	rows?: number;
	onBlur?: FocusEventHandler<
		HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
	>;
	className?: string;
	"aria-describedby"?: string;
	"aria-label"?: string;
	"aria-labelledby"?: string;
	"aria-invalid"?: InputHTMLAttributes<HTMLInputElement>["aria-invalid"];
	"aria-errormessage"?: string;
	"data-testid"?: string;
	inputMode?: InputHTMLAttributes<HTMLInputElement>["inputMode"];
	pattern?: string;
	min?: number | string;
	max?: number | string;
	step?: number | string;
};

function FieldComponent(
	{
		id,
		name,
		label,
		control = "input",
		type = "text",
		value,
		checked,
		onChange,
		options = [],
		helperText,
		error,
		required = false,
		disabled = false,
		readOnly = false,
		placeholder,
		autoComplete,
		rows,
		onBlur,
		className,
		"aria-describedby": ariaDescribedBy,
		"aria-label": ariaLabel,
		"aria-labelledby": ariaLabelledBy,
		"aria-invalid": ariaInvalid,
		"aria-errormessage": ariaErrorMessage,
		"data-testid": dataTestId,
		inputMode,
		pattern,
		min,
		max,
		step,
	}: FieldProps,
	ref: ForwardedRef<FieldControlHandle>,
) {
	const controlRef = useRef<
		HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement | null
	>(null);
	const handleControlRef = (
		element: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement | null,
	) => {
		controlRef.current = element;
	};

	useImperativeHandle(
		ref,
		() => ({
			focus: () => controlRef.current?.focus(),
		}),
		[],
	);

	const describedBy = [
		ariaDescribedBy,
		helperText ? `${id}-help` : null,
		error ? `${id}-error` : null,
	]
		.filter(Boolean)
		.join(" ");
	const rootClassName = [styles.root, className].filter(Boolean).join(" ");
	const commonProps = {
		id,
		name,
		value,
		disabled,
		readOnly,
		required,
		placeholder,
		autoComplete,
		onChange,
		onBlur,
		"aria-describedby": describedBy || undefined,
		"aria-label": ariaLabel,
		"aria-labelledby": ariaLabelledBy,
		"aria-invalid": error ? true : ariaInvalid,
		"aria-errormessage": ariaErrorMessage,
		"data-testid": dataTestId,
		inputMode,
		pattern,
		min,
		max,
		step,
	};

	const labelContent = (
		<>
			<span>{label}</span>
			{required ? <span className={styles.required}>Obligatorio</span> : null}
		</>
	);

	let controlElement: ReactNode;
	if (control === "textarea") {
		controlElement = (
			<textarea
				{...commonProps}
				ref={handleControlRef}
				className={styles.control}
				rows={rows}
			/>
		);
	} else if (control === "select") {
		controlElement = (
			<select
				{...commonProps}
				ref={handleControlRef}
				className={styles.control}
			>
				{options.map((option) => (
					<option key={option.value} value={option.value}>
						{option.label}
					</option>
				))}
			</select>
		);
	} else if (control === "checkbox") {
		controlElement = (
			<label className={styles.checkboxLabel} htmlFor={id}>
				<input
					{...commonProps}
					ref={handleControlRef}
					className={styles.checkbox}
					type="checkbox"
					checked={checked}
				/>
				<span>{labelContent}</span>
			</label>
		);
	} else {
		controlElement = (
			<input
				{...commonProps}
				ref={handleControlRef}
				className={styles.control}
				type={type}
			/>
		);
	}

	return (
		<div className={rootClassName} data-control={control}>
			{control === "checkbox" ? null : (
				<label className={styles.label} htmlFor={id}>
					{labelContent}
				</label>
			)}
			{controlElement}
			{helperText ? (
				<p className={styles.helper} id={`${id}-help`}>
					{helperText}
				</p>
			) : null}
			{error ? (
				<p className={styles.error} id={`${id}-error`} role="alert">
					{error}
				</p>
			) : null}
		</div>
	);
}

const Field = forwardRef<FieldControlHandle, FieldProps>(FieldComponent);
Field.displayName = "Field";

export default Field;
