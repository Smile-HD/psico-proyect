# Delta Spec: identity-auth

# Identity & Auth Specification

## Purpose

Dev-first identity: seeded 3-role accounts, JWT login, deny-by-default role middleware with safe denials and an OIDC seam behind `PSICO_AUTH_MODE`.

## ADDED Requirements

### Requirement: User/Role Schema

The system MUST model `users`, `roles`, and `user_roles`. Roles MUST be exactly `admin`, `psicólogo`, and `evaluado`. The F1 seed MUST create one dev account per role.

#### Scenario: Seeded accounts

- GIVEN a seeded database
- WHEN querying `roles`
- THEN `admin`, `psicólogo`, and `evaluado` exist, each with one dev account

### Requirement: Dev JWT Login

The system MUST expose `POST /api/v1/auth/login` returning an HS256 JWT for valid seeded dev credentials. Auth resolution MUST be isolated behind a single `get_current_user` dependency gated by `PSICO_AUTH_MODE` (F1 value: `dev`), so a future OIDC provider can be swapped in without touching handlers.

#### Scenario: Happy login

- GIVEN valid `psicólogo` credentials
- WHEN the client posts to `/api/v1/auth/login`
- THEN a JWT carrying role `psicólogo` is returned
- AND the audit log records `auth.login`

#### Scenario: OIDC seam isolation

- GIVEN `PSICO_AUTH_MODE=dev`
- WHEN any handler calls `get_current_user`
- THEN it receives the resolved user without inspecting provider details

### Requirement: require_roles Deny-by-default

Every protected route MUST declare `require_roles(...)`; there MUST be no default-allow. The access matrix MUST live in code: `admin` manages users/institutions, publishes instruments, views audit, runs seeds; `psicólogo` reads the catalog, runs sessions, signs/views consent, views results; `evaluado` reads the catalog, runs own sessions, signs/views own consent, views own results.

#### Scenario: Admin allowed

- GIVEN an `admin` JWT
- WHEN calling a seed-management endpoint
- THEN the request succeeds (200)

#### Scenario: Role denied

- GIVEN an `evaluado` JWT
- WHEN calling the audit-log endpoint
- THEN the request fails with 403
- AND no partial data is returned

#### Scenario: No default-allow

- GIVEN a protected route exercised by a user
- WHEN no role list was declared for it
- THEN the request is denied by default with 403

### Requirement: Safe Denials

Auth failures MUST return generic 401/403 messages that never disclose account existence or role. Every denial MUST be written to `audit_log` (event `auth.denied`, outcome `denied`).

#### Scenario: No account disclosure

- GIVEN credentials for an unknown user
- WHEN login is attempted
- THEN the response text is identical to the wrong-password response of an existing user

#### Scenario: Denial audited

- GIVEN an `evaluado` user calling an admin endpoint
- WHEN the request is denied
- THEN `audit_log` gains `auth.denied` with actor id and outcome `denied`

### Requirement: Token Expiry, Refresh & Revocation

JWTs MUST carry an `exp` claim and be rejected after expiry. The system MUST expose a refresh flow for valid sessions and MUST revoke tokens server-side on role change or security event, forcing re-authentication before the new role applies. Revocation MUST be enforced with a deny-list in `dev` mode.

#### Scenario: Expired token rejected

- GIVEN an expired JWT
- WHEN a protected route is called
- THEN the request fails with 401

#### Scenario: Role change forces re-auth

- GIVEN a user whose role changed after login
- WHEN the previous token is presented
- THEN the request is rejected
- AND the user must re-authenticate to obtain a token carrying the new role

