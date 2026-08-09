/**
 * TestPsico — catalog API client (browser side).
 *
 * Spanish UI, English code. Every mutation carries an idempotency key so a
 * timed-out retry never duplicates a side effect; a new user intent gets a
 * fresh key. Server envelopes ({ error: { code, message, request_id,
 * details } }) are unwrapped into typed errors for the UI.
 */

export type ApiErrorPayload = {
	code: string;
	message: string;
	request_id: string;
	details: Record<string, unknown>;
};

export class ApiError extends Error {
	readonly payload: ApiErrorPayload;

	constructor(payload: ApiErrorPayload) {
		super(`${payload.message} (${payload.code})`);
		this.name = "ApiError";
		this.payload = payload;
	}
}

export function apiBase(): string {
	return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

function envelope<T>(body: unknown): T {
	const data = body as { error?: ApiErrorPayload } & T;
	if (data && typeof data === "object" && "error" in (data as object)) {
		throw new ApiError((data as { error: ApiErrorPayload }).error);
	}
	return data;
}

export type RequestOptions = {
	method?: "GET" | "POST" | "PUT";
	token: string;
	idempotencyKey?: string;
	body?: unknown;
};

export async function apiFetch<T>(
	path: string,
	options: RequestOptions,
): Promise<T> {
	const headers: Record<string, string> = {
		Authorization: `Bearer ${options.token}`,
	};
	if (options.idempotencyKey) {
		headers["Idempotency-Key"] = options.idempotencyKey;
	}
	if (options.body !== undefined) {
		headers["Content-Type"] = "application/json";
	}
	const res = await fetch(`${apiBase()}${path}`, {
		method: options.method ?? "GET",
		headers,
		body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
		cache: "no-store",
	});
	const text = await res.text();
	let parsed: unknown = null;
	if (text) {
		try {
			parsed = JSON.parse(text);
		} catch {
			// Non-JSON body (proxy error page, crash) — surface as a stable error.
			throw new ApiError({
				code: "invalid_response",
				message: "El servicio devolvió una respuesta inesperada.",
				request_id: "",
				details: { status: res.status },
			});
		}
	}
	if (!res.ok) {
		// If the server returned a parseable error envelope, throw that.
		// Otherwise synthesize an ApiError from the HTTP status so callers
		// always receive a consistent ApiError (never a silent null resolve).
		if (
			parsed &&
			typeof parsed === "object" &&
			"error" in (parsed as object)
		) {
			throw new ApiError((parsed as { error: ApiErrorPayload }).error);
		}
		throw new ApiError({
			code: `HTTP_${res.status}`,
			message: `El servidor respondió con un error (${res.status} ${res.statusText}).`,
			request_id: "",
			details: { status: res.status, body: parsed },
		});
	}
	return envelope<T>(parsed);
}
