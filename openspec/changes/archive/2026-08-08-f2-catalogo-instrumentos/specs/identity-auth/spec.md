# Delta for Identity & Auth

## MODIFIED Requirements

### Requirement: require_roles Deny-by-default

Every protected route MUST declare `require_roles(...)`; there MUST be no default-allow. The access matrix MUST live in code: `admin` manages users/institutions, manages instruments (creates and edits drafts, archives versions via `manage_instruments`), publishes instruments (`publish_instruments`), views audit, runs seeds; `psicólogo` manages instruments (creates and edits drafts, archives versions) but MUST NOT publish, reads published catalog content only, runs sessions, signs/views consent, views results; `evaluado` reads published catalog content only, runs own sessions, signs/views own consent, views own results. The `read_catalog` capability is corrected to a published-only payload contract for all three roles: drafts and archived versions are never exposed through it, and draft administration is a separate protected surface behind `manage_instruments`.

(Previously: `read_catalog` was granted to all three roles with no published-only distinction, `publish_instruments` was admin-only, and no `manage_instruments` capability existed.)

#### Scenario: Admin allowed

- GIVEN an `admin` JWT
- WHEN calling a seed-management endpoint
- THEN the request succeeds (200)

#### Scenario: Role denied

- GIVEN an `evaluado` JWT
- WHEN calling the audit-log endpoint
- THEN the request fails with 403
- AND no partial data is returned

#### Scenario: Psicólogo cannot publish

- GIVEN a `psicólogo` JWT and a valid draft
- WHEN calling the publish operation
- THEN the request fails with 403
- AND the draft remains unpublished

#### Scenario: No default-allow

- GIVEN a protected route exercised by a user
- WHEN no role list was declared for it
- THEN the request is denied by default with 403
