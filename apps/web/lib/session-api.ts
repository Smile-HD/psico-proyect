import { ApiError, apiFetch } from "./api";

export type SessionStatus = "in_progress" | "completed";

export type PublishedVersionSummary = {
	instrument_version_id: string;
	instrument_key: string;
	title: string;
	version_no: number;
};

export type SessionOption = {
	id: string;
	display_order: number;
	label: string;
	locale: "es";
};

export type SessionItem = {
	id: string;
	item_order: number;
	text: string;
	locale: "es";
	required: boolean;
	response_options: SessionOption[];
	response_option_id?: string | null;
};

export type SessionScale = {
	id: string;
	display_order: number;
	label: string;
	locale: "es";
	items: SessionItem[];
};

export type SessionDetail = {
	id: string;
	status: SessionStatus;
	instrument_version_id: string;
	progress: { answered: number; total: number };
	projection: {
		instrument_version_id: string;
		version_no: number;
		response_type: "likert_1_5";
		scales: SessionScale[];
	} | null;
};

export type SessionCreated = { id: string; status: SessionStatus };
export type SessionSaveResult = SessionCreated & { saved_count: number };
export type SessionResponseInput = {
	item_id: string;
	response_option_id: string;
};

export type SessionErrorKind =
	| "consent_required"
	| "not_found"
	| "validation"
	| "forbidden"
	| "conflict"
	| "unknown";

const ERROR_MESSAGES: Record<SessionErrorKind, string> = {
	consent_required:
		"Antes de iniciar, debe otorgar el consentimiento requerido. Complete el flujo de consentimiento y vuelva a intentarlo.",
	not_found:
		"Esta evaluación ya no está disponible para iniciar. Regrese al listado y elija otra opción.",
	validation: "Revise las respuestas e intente nuevamente.",
	forbidden: "No tiene permisos para acceder a esta evaluación.",
	conflict: "La evaluación no puede modificarse en este momento.",
	unknown: "No se pudo conectar con el servicio. Intente nuevamente.",
};

export class SessionApiError extends Error {
	readonly kind: SessionErrorKind;
	readonly code: string;
	readonly details: Record<string, unknown>;

	constructor(
		kind: SessionErrorKind,
		code: string,
		details: Record<string, unknown> = {},
	) {
		super(ERROR_MESSAGES[kind]);
		this.name = "SessionApiError";
		this.kind = kind;
		this.code = code;
		this.details = details;
	}
}

export function newIntentKey(): string {
	return crypto.randomUUID();
}

export function mapSessionError(error: unknown): SessionApiError {
	if (error instanceof SessionApiError) return error;
	if (!(error instanceof ApiError)) {
		return new SessionApiError("unknown", "unknown");
	}

	const { code, message, details } = error.payload;
	if (message === "consent_required") {
		return new SessionApiError("consent_required", message, details);
	}
	if (code === "NOT_FOUND") return new SessionApiError("not_found", code, details);
	if (code === "VALIDATION_ERROR") {
		return new SessionApiError("validation", code, details);
	}
	if (code === "FORBIDDEN") return new SessionApiError("forbidden", code, details);
	if (code === "CONFLICT") return new SessionApiError("conflict", code, details);
	return new SessionApiError("unknown", code, details);
}

async function request<T>(path: string, options: Parameters<typeof apiFetch>[1]): Promise<T> {
	try {
		return await apiFetch<T>(path, options);
	} catch (error) {
		throw mapSessionError(error);
	}
}

export function listPublishedVersions(token: string) {
	return request<{ versions: PublishedVersionSummary[] }>(
		"/api/v1/catalog/published-versions",
		{ token },
	);
}

export function createSession(
	token: string,
	instrumentVersionId: string,
	idempotencyKey = newIntentKey(),
) {
	return request<SessionCreated>("/api/v1/sessions", {
		method: "POST",
		token,
		idempotencyKey,
		body: { instrument_version_id: instrumentVersionId },
	});
}

export function getSession(token: string, sessionId: string) {
	return request<SessionDetail>(`/api/v1/sessions/${sessionId}`, { token });
}

export function saveSessionResponses(
	token: string,
	sessionId: string,
	responses: SessionResponseInput[],
	idempotencyKey = newIntentKey(),
) {
	return request<SessionSaveResult>(
		`/api/v1/sessions/${sessionId}/responses`,
		{
			method: "PUT",
			token,
			idempotencyKey,
			body: { responses },
		},
	);
}

export function completeSession(
	token: string,
	sessionId: string,
	idempotencyKey = newIntentKey(),
) {
	return request<SessionCreated>(`/api/v1/sessions/${sessionId}/complete`, {
		method: "POST",
		token,
		idempotencyKey,
	});
}
