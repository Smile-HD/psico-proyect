# Tasks: F3 — Evaluation Session & Delivery

- [x] **1. Schemas & DTOs (Pydantic v2)**
  - [x] Create `app/schemas/sessions.py` with SessionCreate, ResponseCreate, SessionResumeResponse, and SessionSubmitResponse.

- [x] **2. API Endpoints (FastAPI)**
  - [x] Implement `POST /api/v1/sessions` (Create & start session locking `instrument_version_id`).
  - [x] Implement `GET /api/v1/sessions/{id}/resume` (Get progress and server-calculated remaining time).
  - [x] Implement `POST /api/v1/sessions/{id}/responses` (Idempotent autosave with `Idempotency-Key`).
  - [x] Implement `POST /api/v1/sessions/{id}/submit` (Freeze responses & mark as `completed`).
  - [x] Register session router in `app/api/router.py`.

- [x] **3. Testing & Verification (Pytest)**
  - [x] Create `tests/test_sessions.py`.
  - [x] Test session creation and locked instrument version.
  - [x] Test idempotent autosave (duplicate request returns existing response).
  - [x] Test network resumption with remaining time calculation.
  - [x] Test timer expiration enforcement on server.
  - [x] Test submission freezing (editing completed session returns 400/409).

- [x] **4. Evaluado UI & Delivery Wizard (Next.js)**
  - [x] Fix permissions or endpoint so `evaluado` users can fetch published test details (`TP-S-01:v1`) without a 403 error.
  - [x] Implement inline consent check/grant before starting the session.
  - [x] Build the step-by-step assessment UI in `apps/web/src/app/sesion/page.tsx` rendering ONE item per screen.
  - [x] Connect silent autosave per click (`POST /responses`), progress bar, and server countdown timer.
  - [x] Implement resumption on page reload (`GET /resume`) and final submission (`POST /submit`).