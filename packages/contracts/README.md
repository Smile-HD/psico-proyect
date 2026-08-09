# TestPsico Contracts

Binding conventions shared by every phase (F1–F6). These live here and in the
OpenSpec specs — not implicitly in code. Technical contract tokens (IDs, error
codes, seed manifest schema) are **English**; human-facing UI texts are
**Spanish**.

## 1. Identifier convention

| Data kind | Format | Namespace / rule |
| --- | --- | --- |
| Runtime rows (sessions, grants, audit, …) | **UUID4** | Any non-seed row created by the application |
| Seed rows | **UUID5** | `uuid5(NAMESPACE_URL, "psico-seed:" + key)` |

- Deterministic seed ids: the same stable key always yields the same UUID5, so
  re-seeding is idempotent (version nibble of the UUID is `5`).
- A runtime row and a seed row are distinguishable by the UUID version nibble
  (`4` vs `5`).

### Stable seed keys (pinned)

| Key | Row |
| --- | --- |
| `evaluado_01` … `evaluado_30` | profile users, their sessions, responses, consent grants |
| `TP-S-01` | synthetic instrument (20 items, version 1 immutable) |
| `RS-TP-S-01` | invented reference set (research-only) |

Internal keys (roles, dev accounts, consent template, item/response rows) use
the same `psico-seed:` namespace with descriptive suffixes, e.g.
`role:admin`, `user:evaluado_01`, `item:TP-S-01:1`, `session:evaluado_01`,
`response:evaluado_01:item:TP-S-01:1`, `consent:v1`, `institution:dev`.

## 2. Error envelope (single, all endpoints, all phases)

Every API error returns exactly:

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "insufficient_role",
    "request_id": "<uuid4>",
    "details": {}
  }
}
```

- `request_id` is unique per request (set by middleware, echoed in responses).
- Codes MUST be one of:

  | Code | Meaning |
  | --- | --- |
  | `VALIDATION_ERROR` | request payload invalid |
  | `UNAUTHORIZED` | missing/invalid credentials |
  | `FORBIDDEN` | authenticated but not allowed |
  | `NOT_FOUND` | resource does not exist |
  | `CONFLICT` | state conflict (e.g. session without consent) |
  | `INTERNAL_ERROR` | unexpected failure (never leaks stack traces) |

- Auth failures return **generic message text only** — they never disclose
  account existence or role (`Unauthorized`), and every denial is written to
  `audit_log` as `auth.denied` with outcome `denied`.

## 3. Audit deny-list

`audit_log.metadata` (JSONB) MUST NOT contain:

- raw response values / answers
- personal data beyond the actor user id
- tokens, passwords, or secrets
- instrument item content

Event catalog: `auth.login`, `auth.denied`, `user.role_changed`,
`instrument.draft_created`, `instrument.draft_updated`, `instrument.published`,
`instrument.archived`, `consent.granted`, `consent.revoked`, `session.started`,
`session.completed`, `session.blocked_without_consent`, `seed.executed`.

`audit_log` is append-only: a DB trigger rejects `UPDATE`/`DELETE`; the app
role holds only `INSERT` + `SELECT` on it.

## 4. Seed manifest schema

`seed_manifest` records one row per seed run:

| Field | Type | Meaning |
| --- | --- | --- |
| `seed_version` | string | e.g. `1.0.0` |
| `counts` | JSONB | per-table seeded row counts |
| `checksum` | string | `sha256` over the fixture files (sorted paths, concatenated bytes) |
| `executed_at` | timestamp | run time |

Seed invariants: every seeded row sets `synthetic = true` and
`source = 'seed'` where those columns exist; `--reset` removes only seed-owned
rows in reverse FK order; all data is research-only.

## 5. Base entities: institution hierarchy

Every row in the institutional hierarchy carries `institution_id` (FK to
`institutions.id`); seed creates one synthetic institution plus one
campus/faculty/program so every later phase can join through the same root.

| Entity | Table | Key fields |
| --- | --- | --- |
| Institution | `institutions` | `id`, `name`, `synthetic`, `source` |
| Campus | `campuses` | `id`, `institution_id`, `name`, `synthetic`, `source` |
| Faculty | `faculties` | `id`, `institution_id`, `name`, `synthetic`, `source` |
| Program | `programs` | `id`, `institution_id`, `name`, `synthetic`, `source` |

- Relationship rule: `campus`/`faculty`/`program` never float without an
  owning institution; the FK is NOT NULL.
- `institution_id` is the join key every downstream phase consumes
  (instrument ownership, session context, reporting rollups).
- All seed rows in this family set `synthetic = true` / `source = 'seed'`.

## 6. Access matrix (deny-by-default)

Every protected route MUST declare `require_roles(...)`; there is no
default-allow. See `services/api/app/core/permissions.py` (source of truth):

| Capability | admin | psicólogo | evaluado |
| --- | --- | --- | --- |
| Manage users/roles | ✅ | ❌ | ❌ |
| Manage institutions | ✅ | ❌ | ❌ |
| Manage instruments (drafts, archive) | ✅ | ✅ | ❌ |
| Publish instrument versions | ✅ | ❌ | ❌ |
| Read published catalog | ✅ | ✅ | ✅ (own) |
| Run sessions | ✅ | ✅ | ✅ (own) |
| Sign/view consent | ✅ (registry) | ✅ | ✅ (own) |
| View results | ✅ | ✅ | ✅ (own) |
| View audit log | ✅ | ❌ | ❌ |
| Run seeds / manifests | ✅ | ❌ | ❌ |

## 7. Instrument catalog (F2)

### 7.1 Four-level model and lifecycle

Instruments follow `instrument → scale → item → response_option`. The MVP
response type is fixed to `likert_1_5`: exactly five ordered options per item
whose server-side values are 1–5; the public payload exposes option *labels*
only, never numeric values or answer keys.

Version lifecycle is `draft → published → archived` with a `CHECK` constraint
and DB triggers: a published or archived version is immutable (no in-place
edits, no delete); archive is the only transition allowed on a published
version; there is no unarchive. Editing always creates a new draft version;
`version_no` auto-increments under a parent-instrument row lock.

Two published versions of the same instrument may coexist and both are
session-startable. The seed instrument `TP-S-01:v1` is read-only in every F2
workflow: the UI never offers it as an editable parent, and the service
rejects any attempt to version it (`seed_catalog_read_only`).

### 7.2 Endpoint surface

All paths are under `/api/v1/catalog`. Every mutating endpoint requires an
`Idempotency-Key` header.

| Method and path | Roles | Purpose |
| --- | --- | --- |
| `GET /published-versions/{version_id}` | admin, psicólogo, evaluado | Published-only evaluator payload (labels, no values) |
| `GET /admin/instruments` | admin, psicólogo | Paginated authoring list (`page`, `page_size` ≤ 100, `key`, `status`) |
| `GET /admin/instruments/{instrument_id}` | admin, psicólogo | Admin detail; seed is marked read-only |
| `POST /admin/instruments` | admin, psicólogo | Create runtime instrument + initial draft |
| `POST /admin/instruments/{instrument_id}/versions` | admin, psicólogo | Allocate a new draft (optionally cloned from a runtime published version) |
| `GET /admin/versions/{version_id}` | admin, psicólogo | Full authoring representation |
| `PUT /admin/versions/{version_id}/content` | admin, psicólogo | Atomically save the complete draft aggregate |
| `POST /admin/versions/{version_id}/publish` | admin | Validate and publish a draft |
| `POST /admin/versions/{version_id}/archive` | admin, psicólogo | Archive a published version |

Non-published IDs are indistinguishable from missing IDs on the published
read route (`NOT_FOUND`); administration routes deny non-authorized roles with
`FORBIDDEN` before touching any resource, and `auth.denied` is recorded.

### 7.3 Idempotency rules

- Every create/save/publish/archive call carries one `Idempotency-Key` per
  user intent. A timed-out retry reuses the key; a new intent gets a new key.
- Replaying the same key and body returns the original response with no
  duplicated side effect (no extra version, transition, or audit event).
- Same key with a different body returns `CONFLICT` and performs no second
  side effect.
- Records are retained indefinitely (ADR-003).

### 7.4 Error codes (catalog)

`VALIDATION_ERROR` (incomplete/inconsistent aggregate), `FORBIDDEN`
(role gate), `NOT_FOUND` (missing or non-published read), `CONFLICT`
(immutable mutation, archive of a draft, same-key-different-body), and
`seed_catalog_read_only` for any operation on the seed instrument. Every
error follows the single envelope with `request_id` (section 2).

### 7.5 F3 handoff contract

F3 (session) consumes: the `instrument_version_id` copied verbatim into each
session and never changed; the published read payload for rendering; the
freezing rule (published versions never change; a new version is a new id);
and stable errors for draft/archived/missing/invalid versions. F4 consumes
the item ↔ scale ↔ option relationship with the server-side 1–5 mapping via
a non-public fixture projection.

### 7.6 Evaluation sessions (F3)

F3 owns the consent-gated session lifecycle and response persistence. The web
client uses option identifiers and labels only; scoring and result computation
belong to F4.

#### 7.6.1 Endpoint surface

All session paths are under `/api/v1/sessions`. Protected routes allow `admin`,
`psicólogo`, and `evaluado`, with session reads and writes scoped to the owner
except for the documented admin operational override.

| Method and path | Purpose |
| --- | --- |
| `GET /catalog/published-versions` | Discovery-safe published summaries: identifiers and labels only. |
| `POST /sessions` | Start an `in_progress` session for a published version. |
| `GET /sessions` | List the caller's sessions. |
| `GET /sessions/{session_id}` | Read status, progress, pinned projection, and owner answers as option IDs. |
| `PUT /sessions/{session_id}/responses` | Atomically upsert a batch of `item_id`/`response_option_id` pairs. |
| `POST /sessions/{session_id}/complete` | Complete after every required item has an answer. |

#### 7.6.2 Published-only gate and no-leak behavior

Session creation checks the published-version gate before consent. Missing,
malformed, draft, archived, and unknown `instrument_version_id` values all
return the same `NOT_FOUND` / `resource_not_found` envelope. The response does
not disclose whether a non-published version exists, and the rejected request
creates neither a session row nor a session audit event. A valid published
request without a granted consent returns `CONFLICT` / `consent_required` and
records only the existing `session.blocked_without_consent` audit event.

#### 7.6.3 Mutation idempotency

`POST /sessions`, `PUT /sessions/{session_id}/responses`, and
`POST /sessions/{session_id}/complete` require `Idempotency-Key`. The existing
consent mutations also require it:
`POST /consent/{version_id}/grant` and `POST /consent/{version_id}/revoke`.
One key represents one intent; a retry with the same body replays the original
result without duplicate rows or audit events. Reusing a key with a different
body returns `CONFLICT` / `idempotency_key_reused` and has no side effect.

#### 7.6.4 Labels-only and no-scoring boundary

Published discovery and session projections expose human-facing labels and
stable identifiers. Response options are submitted and returned as
`response_option_id`; the server owns the private option-to-value mapping.
Numeric option values, answer keys, scores, percentiles, transformed results,
and reference-set results MUST NOT cross the public API or appear in the web
UI. F4 may consume the private mapping later; F3 completion returns lifecycle
state only.
