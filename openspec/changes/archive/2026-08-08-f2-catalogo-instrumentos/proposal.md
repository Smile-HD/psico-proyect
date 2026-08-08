# Proposal: F2 — Instrument Catalog

## Proposal status

- **Change:** `f2-catalogo-instrumentos`
- **State:** proposed
- **Phase:** F2 — Instrument Catalog
- **Primary owner:** Trevor
- **Affected phases and owners:** F1 contracts, permissions, audit, seed, and schema conventions (Marces); F2 implementation (Trevor); F3 session consumption (Jhamil); F4 scoring fixtures and relationship consumption (Juan Carlos).

## Problem statement

F1 provides a seeded, immutable `TP-S-01:v1`, but it does not yet provide a catalog product. There are no instrument endpoints, catalog schemas, management permissions, or editing UI. The current instruments family stores a denormalized scale name on `instrument_items`, has no `scales` or `response_options` tables, and permits free-text version statuses. The existing catalog exposure also grants `evaluado` access to the same `read_catalog` capability without a published-only payload contract.

Without F2, a psychologist cannot create and maintain synthetic instruments while preserving historical versions, and F3 cannot reliably render a published version or pin a session to the exact instrument definition used. F2 must close these gaps without editing the seeded version, exposing answer keys, introducing real psychometric claims, or changing the immutable-versioning invariant.

## Product outcome

A psychologist can create and maintain synthetic instrument drafts through the catalog UI, an administrator can publish them, and all authorized users can read a safe published-version payload. Publishing freezes the complete hierarchy and creates a stable `instrument_version_id` for downstream sessions and scoring. Multiple published versions of one instrument remain independently addressable, so historical sessions and future sessions can use the intended version.

## Goals

1. Model the complete MVP hierarchy: `instrument → scale → item → response_option` inside an identifiable instrument version.
2. Provide draft creation, editing, publication, and archive workflows with deny-by-default role enforcement.
3. Enforce immutable published and archived versions; editing always creates or updates a draft version and never changes a published version.
4. Publish a read contract that gives F3 everything required to render a session while withholding answer keys and internal rules.
5. Make all F2 mutations idempotent and record the agreed catalog audit events without item content.
6. Keep all seed, fixture, and runtime catalog content synthetic and marked `synthetic`/`research-only`.

## Non-goals and scope boundaries

F2 does **not** include:

- Scoring, baremos, profiles, program recommendations, or reporting.
- Real psychometric content, institutional validity claims, or production diagnostic use.
- In-place editing of a published version.
- LLM use for creating, scoring, or explaining items.
- Admissions, employment, hiring, rejection, or other high-impact decisions.
- Refresh/revocation or audit-outage resilience follow-ups from F1, except the F1 idempotency requirement that directly constrains F2 mutations.
- Institution ownership on instruments in the MVP; this is explicitly deferred.
- F3 session-state implementation or session UI. F2 publishes the catalog contract and F3 owns session enforcement and consumption.

## Binding product decisions

### D1 — Seed policy and coexistence

`TP-S-01:v1` is **read-only in all F2 workflows**. The F2 UI MUST NOT edit it, create a new version under the seed instrument, or treat its seed content as runtime-authorable content. It remains the synthetic, research-only reference used by existing seed sessions and `RS-TP-S-01`.

Runtime instruments and versions MUST use their own runtime rows and MUST NOT create foreign-key dependencies from runtime catalog content to seed-owned instrument, version, or item rows. Runtime creation using a seed key or a seed entity as an editable parent is rejected.

`seed --reset` MUST perform an atomic dependency preflight. If any non-seed row references a seed-owned catalog row, reset MUST stop with a stable conflict and make no deletion; it MUST never delete a seed parent and leave a runtime foreign key broken. Under the normal F2 rule, runtime rows are separate roots, so seed reset can recreate the seed graph without affecting runtime instruments or versions. This is the documented coexistence rule.

### D2 — Permissions and published visibility

The capability matrix is extended as follows:

- `admin`: full catalog administration, including creating/editing drafts, publishing, and archiving.
- `psicólogo`: create and edit drafts and archive versions; cannot publish.
- `evaluado`: read published versions only; cannot access catalog administration or drafts.

The existing `read_catalog` exposure is corrected so that it never exposes drafts or archived versions to `evaluado`. Draft administration is a separate protected surface. Deny-by-default `require_roles(...)`, the F1 error envelope, and generic authorization behavior remain mandatory.

### D3 — Four-level model and MVP response type

The instruments family is amended from the ratified F1 three-table shape to the four-level model `instrument → scale → item → response_option`. The MVP fixes `response_type` to `likert_1_5`. Each item has five ordered response options whose server-side values are exactly 1–5; option labels are modeled explicitly and are synthetic.

No alternative response type is introduced in F2. This preserves compatibility with the existing `responses.value BETWEEN 1 AND 5` invariant and gives F4 an exact item-to-scale-to-option relationship.

### D4 — Audit and idempotency

Every F2 mutating endpoint MUST accept `Idempotency-Key` and replay the original result without duplicating the side effect. This is an implementation of the ratified contracts requirement, not an exception.

F2 adds the following catalog audit events to the existing event catalog: `instrument.draft_created`, `instrument.draft_updated`, `instrument.published`, and `instrument.archived`. The existing `instrument.published` event remains the canonical publication event. `draft_updated` is emitted on an explicit successful save, not for every unsaved field change or internal persistence operation.

Audit metadata is limited to safe metadata such as actor, instrument/version identifiers, `version_no`, and aggregate counts. It MUST NOT contain item text, response-option keys or values, raw responses, tokens, PII, or other denied content.

## F1 gaps absorbed and resolutions

| Gap | F2 resolution |
| --- | --- |
| **G1 — Missing `scales` and `response_options`** | Amend the instruments family to the four-level model and append one schema-only migration to the existing linear Alembic chain. The migration/backfill must preserve seed identity and existing foreign-key semantics; exact migration mechanics belong to design. |
| **G2 — Missing management capability and unsafe broad read capability** | Add `manage_instruments` for `admin` and `psicólogo`; retain `publish_instruments` for `admin`; split protected administration from published reading; make `evaluado` published-only. |
| **G3 — Seed reset foreign-key risk** | Apply D1: seed content is reference-only, runtime content cannot depend on seed catalog rows, and reset aborts atomically on unexpected non-seed dependencies. |
| **G4 — Sessions accept drafts** | The F2 read endpoint returns published versions only. The session-creation status gate is explicitly owned by F3 and must reject a non-published `instrument_version_id`; F2 hands Jhamil the status rule and error cases. F2 does not silently change F3 session behavior in this proposal. |
| **G5 — Free-text version status** | Constrain the lifecycle to `draft → published → archived`. Published and archived versions are immutable. There is no unarchive transition in the MVP; a replacement is a new draft/version. |
| **G6 — Narrow audit catalog** | Add the four catalog event concepts in D4 and update the contract event catalog and its tests in the implementation/spec work. Metadata remains aggregate and content-free. |
| **G7 — Missing idempotency implementation** | Implement `Idempotency-Key` on every F2 `POST`, `PUT`, and `PATCH` mutation, including create, save/update, publish, and archive operations. A repeated key for the same resource replays the original response and does not duplicate audit or data side effects. |
| **G8 — Responses fixed to Likert 1–5** | Keep `likert_1_5` as the only MVP response type and model five labeled options per item with server-side values 1–5. Generalized response types are deferred. |
| **G9 — Missing `institution_id`** | Defer instrument ownership to a later phase with a documented exception. F2 remains institution-agnostic as required by the current configuration; no nullable placeholder is added merely to imply ownership. |
| **G10 — F1 platform follow-ups** | Absorb only idempotency because it is a direct F2 contract requirement. Token refresh/revocation and audit-outage resilience remain outside F2. |
| **G11 — No catalog API, schemas, or UI** | Treat the catalog as a greenfield F2 surface built on F1 conventions: FastAPI/Pydantic contracts, the single error envelope, role guards, Spanish UI text, synthetic seed conventions, and the linear schema chain. |

## F2 contract surface

The following is the product-level contract to be made precise in spec and design. Physical column names, indexes, migration details, and exact request/response DTOs are implementation details for those phases.

### Logical schemas

#### `instrument`

- Stable UUID identifier: UUID4 for runtime rows; deterministic UUID5 for seed rows.
- Unique human-readable `key`, title, description, `synthetic`, and `source`.
- One or more ordered versions.
- No `institution_id` in the MVP; institution ownership is deferred.

#### `instrument_version`

- `instrument_version_id`: stable UUID primary identifier exposed to downstream consumers.
- Parent `instrument_id` and unique `version_no` within an instrument.
- `status`: exactly `draft`, `published`, or `archived`.
- Creation, publication, and archive timestamps as applicable.
- `is_immutable`: false only while draft; true once published and retained true when archived.
- `synthetic` and `source` metadata.
- A published version cannot be updated, deleted, or replaced in place.

#### `scale`

- Stable identifier and parent `instrument_version_id`.
- Synthetic, localized display name/label and a unique positive order within the version.
- A scale belongs to exactly one version; cross-version or cross-instrument attachment is invalid.

#### `item`

- Stable identifier and parent scale identifier.
- Synthetic item text, `locale`, positive order within its scale, and a `required` flag.
- The item belongs to exactly one scale and therefore exactly one version.
- The MVP uses Spanish user-facing content (`locale=es`); localization expansion is deferred.

#### `response_option`

- Stable identifier and parent item identifier.
- Synthetic localized label and positive display order.
- Fixed server-side Likert value in the inclusive range 1–5, with exactly one option for each value per item.
- The evaluator-facing read payload omits the numeric value and other answer-key/internal scoring data; it returns only what is needed to render labels and submit stable option identifiers.

### Validation, locale, adaptation, and availability rules

- A publishable version MUST contain at least one scale, each scale at least one item, and each item exactly five response options.
- Orders MUST be positive, unique within their parent, and contiguous from 1 for deterministic rendering.
- Parent membership and version consistency MUST be validated at write and publish time.
- `required` is explicit item metadata and is honored by F3 when it validates completion.
- `response_type` is `likert_1_5` for every F2 version; other types are rejected as unsupported.
- Human-facing labels and item text are Spanish in the MVP; contract tokens and error codes remain English.
- Adaptation is descriptive metadata only in F2. It MUST NOT dynamically alter the published item set or branch a session; adaptive behavior is deferred.
- Availability is status-based in the MVP: only `published` versions are available through the evaluator-facing read endpoint. Archived versions remain addressable for historical references but are not offered as new catalog choices.
- All data used by tests, fixtures, seed, and the product demonstration MUST be synthetic and marked `synthetic`/`research-only`.

### Lifecycle and coexistence

- `draft → published` is an administrator-only transition after all validation passes.
- `published → archived` is an explicit archive transition available to `psicólogo` and `admin`.
- Drafts are editable by `psicólogo` and `admin`; a draft save does not mutate any published version.
- Published versions are immutable and retain their identifier, timestamps, hierarchy, and audit history.
- Archived versions remain immutable and are never physically deleted by normal catalog operations.
- Multiple published versions of the same instrument MAY coexist. Each has a distinct `instrument_version_id` and `version_no`, and each can be queried independently. Creating a change to a published version creates a new draft/version rather than editing the published row.
- Existing sessions remain pinned to their original published `instrument_version_id`; archiving does not rewrite or invalidate historical session references. Whether a new session may use an archived version is denied by the F3 session gate.

### Endpoint surface

The final URL nesting is a design-phase decision, but F2 publishes these logical operations:

- **Published read:** authenticated `admin`, `psicólogo`, and `evaluado` can request one published version by `instrument_version_id` (optionally with its instrument key). Draft and archived versions are not exposed through this endpoint.
- **Administration:** protected endpoints allow `admin` and `psicólogo` to list and inspect authorized catalog content, create instruments/drafts, and save draft hierarchy content.
- **Publish:** a protected operation available only to `admin` validates and transitions a draft to `published`.
- **Archive:** a protected operation available to `psicólogo` and `admin` transitions a published version to `archived`.
- **Mutation headers:** all create, update/save, publish, and archive operations require `Idempotency-Key`.
- **Errors:** invalid hierarchy/publication returns the stable F1 error envelope with a stable `VALIDATION_ERROR`; role failures use `FORBIDDEN`; inaccessible draft/archive reads do not leak existence through the evaluator-facing endpoint.

The published read payload MUST include the hierarchy, ordering, locale, labels, required flags, and stable option identifiers needed to render a session. It MUST NOT include response-option numeric values, answer keys, scoring rules, hidden internal notes, or item content not intended for that version.

### `instrument_version_id` semantics

`instrument_version_id` identifies the exact immutable version, not merely the instrument or a displayable version number. When F3 creates a session, it MUST copy this identifier into the session and keep it unchanged for the session lifetime. Responses and downstream scoring fixtures resolve against that same version. A new catalog version always receives a new identifier; no session may be re-pointed to another version as a side effect of editing, publishing, or archiving.

### Audit contract

The four catalog events are emitted as follows:

- `instrument.draft_created`: successful creation of an instrument or draft version.
- `instrument.draft_updated`: successful explicit save of a draft.
- `instrument.published`: successful draft-to-published transition.
- `instrument.archived`: successful published-to-archived transition.

Each event includes only safe metadata such as actor, instrument/version identifiers, version number, status transition, and aggregate counts. Item text, option values/keys, raw responses, tokens, and PII are prohibited.

## Acceptance criteria

The following criteria derive from the F2 reparto and are the product acceptance boundary:

1. Trevor can create a synthetic instrument from the interface with at least two scales and multiple items, save it as a draft, and see validation errors for invalid hierarchy/order/response data.
2. An administrator can publish a valid draft. Publication assigns stable ID, status, timestamps, and audit metadata; the complete version becomes immutable.
3. Editing a published instrument never changes its items or options. The workflow creates a distinct draft/version with a new `instrument_version_id`.
4. Two versions of the same instrument can coexist as published versions and can be queried independently.
5. An invalid version cannot be published and returns the stable error envelope without a partial transition.
6. `admin`, `psicólogo`, and `evaluado` permissions match D2 for create, edit, publish, archive, and read operations; `evaluado` cannot read drafts or archived content.
7. The published read response contains everything required to render the session, including ordered scales/items/options, locale, labels, and required flags, but does not expose answer keys or internal rules.
8. Every F2 mutation is idempotent under `Idempotency-Key`; retries do not duplicate versions, transitions, or audit events.
9. A published version remains immutable after archive, and existing references continue to resolve to the same `instrument_version_id`.
10. `seed --reset` cannot create a foreign-key violation when runtime catalog content exists; unexpected cross-ownership is rejected atomically.
11. F3 receives the published-version payload, the published-only availability rule, the immutable freezing rule, the exact `instrument_version_id` semantics, and stable non-published/error cases.
12. F4 receives synthetic response fixtures and the exact item → scale → response-option relationship, with no real psychometric claims.

## Handoff commitments

### F3 — Jhamil

F2 will hand off:

- A published-only read contract and payload sufficient to render a session.
- The immutable `instrument_version_id` rule: copy it at session creation and never change it.
- The lifecycle rule and stable errors for draft, archived, missing, or invalid versions.
- The explicit ownership requirement that session creation reject non-published versions, including the current F1 draft-acceptance gap.
- Synthetic fixtures and ordering/required-field semantics needed for completion validation.

### F4 — Juan Carlos

F2 will hand off:

- Synthetic, `research-only` fixture content only.
- The exact `instrument_version_id → scale → item → response_option` relationship.
- Stable item and option identifiers and the server-side 1–5 Likert mapping through a non-public fixture/internal contract.
- The guarantee that published hierarchy content and historical session references do not mutate.

## Risks and rollback plan

| Risk | Mitigation and rollback |
| --- | --- |
| **Schema migration or seed backfill breaks existing F1 references.** | Use one additive, linear schema migration with deterministic seed preservation and preflight checks. Before production rollout, verify existing `TP-S-01:v1`, sessions, responses, and `RS-TP-S-01` references. If the migration fails before data adoption, stop and restore the database snapshot or revert the unapplied migration in non-production. If runtime data already exists, do not destructively downgrade; roll back the application release and use a forward corrective migration or restore a verified snapshot. |
| **Published immutability is accidentally bypassed.** | Enforce status/immutability checks at the database and service boundaries. A release rollback MUST never delete or edit published rows; it reverts application behavior while preserving immutable data and audit history. Any discovered mutation requires a maintainer-approved data repair that creates a successor version rather than rewriting history. |
| **Seed reset deletes a parent needed by runtime content.** | Enforce D1's no-cross-ownership rule and atomic reset dependency preflight. On any unexpected dependency, return conflict and make no deletion. If a reset implementation violates this, disable/reset-revert the release and restore from the last verified snapshot; do not force-delete rows. |
| **Drafts or answer keys leak through the read API.** | Separate published read and administration routes, apply role guards, use contract tests for `evaluado`, and omit option values/internal rules from the evaluator payload. If a leak is found, remove/disable the affected read surface, preserve audit evidence, and release a corrected contract without altering catalog data. |
| **Idempotency or audit duplication during retries.** | Persist and verify idempotency results around the complete mutation, including audit emission. On failure, stop retries for the affected key, inspect the recorded result, and apply a corrective migration or replay-safe repair; never manually duplicate audit events. |
| **F3/F4 assumptions diverge from the published hierarchy.** | Treat the handoff payload and fixtures as versioned contracts. F3/F4 integration checks must use stable `instrument_version_id` fixtures. A contract mismatch is resolved by a new versioned contract or successor implementation, not by changing a published version. |

## Open questions for spec/design

No additional product decision is required to start the next phase. The following implementation details remain intentionally open for `spec` and `design`:

1. Exact URL paths, DTO names, pagination/filtering, and whether administration lists are scoped by instrument key or `instrument_version_id`.
2. The precise database column migration/backfill from F1's denormalized `instrument_items.scale` to `scales` and `response_options`, including compatibility treatment for existing seed rows.
3. The concrete idempotency record scope, retention policy, and behavior when the same key is reused with a different request body.
4. The exact representation of locale and descriptive adaptation metadata, while retaining the MVP rules `locale=es` and no adaptive branching.
5. The concurrency rule for allocating `version_no` and creating a draft when two administrators act simultaneously.
6. The exact error details for non-published reads, publication validation failures, archive conflicts, and seed-reset preflight conflicts, while preserving the F1 error codes and envelope.
7. The final admin UI information architecture and confirmation behavior for publish/archive; these must not weaken the permission or immutability decisions above.
