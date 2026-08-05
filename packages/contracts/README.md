# TestPsico Contracts

Binding conventions shared by every phase (F1–F6). These live here and in the
OpenSpec specs — not implicitly in code. Technical contract tokens (IDs, error
codes, seed manifest schema) are **English**; human-facing UI texts are
**Spanish**.

## 1. Identifier convention

| Data kind | Format | Namespace / rule |
|---|---|---|
| Runtime rows (sessions, grants, audit, …) | **UUID4** | Any non-seed row created by the application |
| Seed rows | **UUID5** | `uuid5(NAMESPACE_URL, "psico-seed:" + key)` |

- Deterministic seed ids: the same stable key always yields the same UUID5, so
  re-seeding is idempotent (version nibble of the UUID is `5`).
- A runtime row and a seed row are distinguishable by the UUID version nibble
  (`4` vs `5`).

### Stable seed keys (pinned)

| Key | Row |
|---|---|
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
  |---|---|
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

Event catalog (F1): `auth.login`, `auth.denied`, `user.role_changed`,
`instrument.published`, `consent.granted`, `consent.revoked`,
`session.started`, `session.completed`, `session.blocked_without_consent`,
`seed.executed`.

`audit_log` is append-only: a DB trigger rejects `UPDATE`/`DELETE`; the app
role holds only `INSERT` + `SELECT` on it.

## 4. Seed manifest schema

`seed_manifest` records one row per seed run:

| Field | Type | Meaning |
|---|---|---|
| `seed_version` | string | e.g. `1.0.0` |
| `counts` | JSONB | per-table seeded row counts |
| `checksum` | string | `sha256` over the fixture files (sorted paths, concatenated bytes) |
| `executed_at` | timestamp | run time |

Seed invariants: every seeded row sets `synthetic = true` and
`source = 'seed'` where those columns exist; `--reset` removes only seed-owned
rows in reverse FK order; all data is research-only.

## 5. Access matrix (deny-by-default)

Every protected route MUST declare `require_roles(...)`; there is no
default-allow. See `services/api/app/core/permissions.py` (source of truth):

| Capability | admin | psicólogo | evaluado |
|---|---|---|---|
| Manage users/roles | ✅ | ❌ | ❌ |
| Manage institutions | ✅ | ❌ | ❌ |
| Publish instrument versions | ✅ | ❌ | ❌ |
| Read published catalog | ✅ | ✅ | ✅ (own) |
| Run sessions | ✅ | ✅ | ✅ (own) |
| Sign/view consent | ✅ (registry) | ✅ | ✅ (own) |
| View results | ✅ | ✅ | ✅ (own) |
| View audit log | ✅ | ❌ | ❌ |
| Run seeds / manifests | ✅ | ❌ | ❌ |
