# Catalog Permissions Specification

## Purpose

The F2 catalog capability matrix (D2): `manage_instruments` for `admin` and `psicólogo`, `publish_instruments` for `admin`, and a corrected published-only `read_catalog` exposure. This spec amends the ratified identity-auth access matrix; the corresponding delta is in `specs/identity-auth/spec.md` in this change.

## Requirements

### Requirement: Catalog Capability Matrix

Catalog capabilities MUST be exactly:

- `manage_instruments` — granted to `admin` and `psicólogo`: create and edit drafts, save draft hierarchy, list and inspect authorized catalog content, and archive published versions. A `psicólogo` MUST NOT publish.
- `publish_instruments` — granted to `admin` only: publish a validated draft.
- `read_catalog` — granted to `admin`, `psicólogo`, and `evaluado`: read published versions only, through the published read endpoint.

#### Scenario: Psicólogo manages drafts and archives

- GIVEN an authenticated `psicólogo` user
- WHEN the user creates a draft, saves it, and later archives its published version
- THEN every operation succeeds
- AND each is audited with the corresponding catalog event

#### Scenario: Psicólogo cannot publish

- GIVEN an authenticated `psicólogo` user and a valid draft
- WHEN the user attempts to publish it
- THEN the response is `FORBIDDEN` with the stable envelope
- AND `auth.denied` is recorded

#### Scenario: Admin publishes

- GIVEN an authenticated `admin` user and a valid draft
- WHEN the user publishes it
- THEN the version becomes `published`
- AND `instrument.published` is recorded

### Requirement: Published-only read_catalog

The existing `read_catalog` exposure MUST be corrected so that it never exposes drafts or archived versions to `evaluado` (or any role through the evaluator-facing endpoint). Draft administration MUST be a separate protected surface reachable only through `manage_instruments`. `evaluado` MUST have no access to catalog administration and MUST receive `NOT_FOUND` (never a status leak) for draft or archived ids through the read endpoint.

#### Scenario: Evaluado reads published only

- GIVEN an authenticated `evaluado` user
- WHEN the user requests a published version
- THEN the read succeeds
- AND draft and archived ids return `NOT_FOUND` with no existence or status leak

#### Scenario: Evaluado blocked from draft administration

- GIVEN an authenticated `evaluado` user
- WHEN the user calls a draft administration endpoint
- THEN the response is `FORBIDDEN`
- AND no draft data is returned

### Requirement: Deny-by-default Catalog Routes

Every catalog route MUST declare `require_roles(...)`; there MUST be no default-allow for any new catalog endpoint. Role failures MUST return the generic F1 `FORBIDDEN` envelope and MUST be audited as `auth.denied` with outcome `denied`, per the ratified identity-auth and audit-consent specs.

#### Scenario: No default-allow on new routes

- GIVEN a new catalog route exercised by any user
- WHEN no role list was declared for it
- THEN the request is denied by default with 403
