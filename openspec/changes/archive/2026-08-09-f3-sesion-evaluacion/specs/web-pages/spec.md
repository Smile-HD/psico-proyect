# Web Pages Specification

## Purpose

The F3 evaluation-session web surface (capability `evaluation-session-ui`, filed under the `web-pages` domain following the F2 UX convention): published-version discovery and start, interactive session with autosave/resume, completion feedback, and evaluado navigation. Reuses the frozen Spanish design system: all copy in Spanish, WCAG 2.2 AA, no scores exposed.

## Requirements

### Requirement: Evaluation Discovery and Start

`/evaluacion` MUST list published versions for authenticated users through the published-version listing, showing labels only. Starting a session MUST create it via the sessions API; when the API returns `consent_required`, the page MUST present an explained Spanish consent state instead of a generic error and MUST NOT create a session. The stable `NOT_FOUND` from creation MUST render as a neutral unavailable state that never reveals draft/archived existence.

#### Scenario: Evaluado starts a session

- GIVEN an authenticated `evaluado` with granted consent and a published version
- WHEN the user starts the session from `/evaluacion`
- THEN a session is created
- AND the user is taken to `/evaluacion/sesiones/[id]`

#### Scenario: Consent missing is explained

- GIVEN an `evaluado` without granted consent
- WHEN the user attempts to start a session
- THEN an explained Spanish consent state renders
- AND no session is created

### Requirement: Session Interaction with Autosave

`/evaluacion/sesiones/[id]` MUST render the pinned version through the published read payload with the LikertMatrix in interactive mode (controlled radios, `aria-label` per cell, visible focus). Answers MUST autosave through debounced `apiFetch` calls carrying an `Idempotency-Key` per intent; saved answers MUST be restored from the session detail on resume; save feedback MUST be announced via `role="status"` and a failed save MUST keep the local state with a retry, never losing input. Required items MUST be marked in text. The page SHALL NOT display scores or reference-set results.

#### Scenario: Answers autosave and resume

- GIVEN a user answering the matrix
- WHEN an answer changes
- THEN the batch saves after the debounce with an idempotency key
- AND after a reload the saved answers are pre-filled

#### Scenario: Completion blocked until required answered

- GIVEN required items unanswered
- WHEN the user attempts completion
- THEN the UI blocks completion
- AND the missing required items are marked in text

### Requirement: Completion Feedback

After a successful `POST /complete`, the page MUST show a Spanish completion confirmation. When completion fails validation, the page MUST keep the session usable and explain the missing required items. Completion feedback MUST NOT show any score.

#### Scenario: Confirmed completion

- GIVEN a session with all required items answered
- WHEN completion succeeds
- THEN a Spanish confirmation renders
- AND no score is displayed

### Requirement: Evaluado Navigation Entry

The NavBar MUST render an evaluation entry with Spanish copy and active-route semantics for authenticated users holding the `run_sessions` capability, including `evaluado`. The entry MUST NOT render for anonymous users.

#### Scenario: Evaluado sees the entry

- GIVEN an authenticated `evaluado`
- WHEN the NavBar renders
- THEN an evaluation entry with Spanish copy is present

### Requirement: Accessibility and Copy

The F3 pages MUST meet WCAG 2.2 AA per the frozen design system: keyboard-operable Likert radios, visible focus, live-region announcements for autosave and completion, reduced-motion respected. All UI copy MUST be Spanish and sober, with no marketing or clinically-validated claims.

#### Scenario: Keyboard-only interaction

- GIVEN a keyboard user on the session page
- WHEN navigating and answering the matrix
- THEN every radio is reachable and operable with visible focus

#### Scenario: Autosave announced

- GIVEN a saved answer batch
- WHEN the save succeeds or fails
- THEN a polite Spanish status announcement renders
