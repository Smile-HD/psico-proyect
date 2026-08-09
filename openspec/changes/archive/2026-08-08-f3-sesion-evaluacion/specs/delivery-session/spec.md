# Capability Spec: Delivery Session & Evaluado UI (F3)

## ADDED REQUIREMENTS

### Requirement: Evaluado Instrument Access
The system MUST allow users with the `evaluado` role to view and access active published instruments.
- **Scenario:** Evaluado accesses test page
  - **GIVEN** an authenticated user with the `evaluado` role
  - **WHEN** they navigate to `/sesion`
  - **THEN** the system fetches published instrument details (`TP-S-01:v1`) without throwing authorization or 403 errors.

### Requirement: Inline Consent Flow
The system MUST enforce and present consent verification before starting an evaluation.
- **Scenario:** Missing consent grant
  - **GIVEN** an `evaluado` user without an active consent record
  - **WHEN** they attempt to start a test session
  - **THEN** an inline consent agreement screen is displayed, requiring explicit acceptance before calling `POST /api/v1/sessions`.

### Requirement: One-Item-Per-Screen Assessment UI
The user interface MUST present questions sequentially (one item per screen), display a progress indicator, enforce server timer synchronization, and record answers silently.
- **Scenario:** Progressing through assessment
  - **GIVEN** an active session in `in_progress` state
  - **WHEN** the user selects an answer for the current item
  - **THEN** an HTTP POST request is sent to `/api/v1/sessions/{id}/responses` with `Idempotency-Key`, updating progress and advancing smoothly.

### Requirement: Session Finalization & Resumption
The system MUST allow seamless resumption upon network failure and lock answers upon submission.
- **Scenario:** Reconnecting mid-test
  - **GIVEN** an interrupted session with saved responses
  - **WHEN** the user reloads `/sesion`
  - **THEN** the client fetches `GET /api/v1/sessions/{id}/resume`, restoring answered items and exact server remaining time.