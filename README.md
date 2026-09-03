# MedSync QA Automation

## 1. Project Overview

MedSync is a multi-tenant Hospital EMR (Electronic Medical Records) SaaS
platform. This repository contains API-level test automation built with
**pytest** and **requests**, covering Authentication, Patient Registration
& Search, and Billing (including the real clinical billing-clearance
workflow). It sits alongside a full manual QA process — Requirement
Analysis, Risk Register, Test Plan, and manual Test Cases — and this
automation implements the stable, regression-worthy subset of that manual
coverage, per the project's documented Test Pyramid strategy.

## 2. Architecture

```
07_Automation/
├── TEST_AUTOMATION_STRATEGY.md   — overall pyramid philosophy (API/UI split)
└── API/
    ├── AUTOMATION_STRATEGY.md    — scope, priorities, entry/exit criteria
    ├── API_TEST_MAPPING.md       — endpoint-by-endpoint mapping from the real OpenAPI spec
    ├── conftest.py               — ROOT fixtures: base_url, login throttling,
    │                                and a role-based auth system (see below)
    ├── pytest.ini                — marker definitions (smoke/regression/negative/critical)
    └── tests/
        ├── authentication/       — login, logout, password management
        ├── patients/             — registration, search, profile
        └── billing/              — invoices, HMO claims, encounter billing-clearance
```

**Root vs. local `conftest.py`:** fixtures in the root `conftest.py` apply
project-wide (every module needs `base_url` and the ability to log in).
Each module folder has its own local `conftest.py` for fixtures only that
module needs (e.g. `unique_phone` in `patients/`), keeping module-specific
setup out of the shared root file.

**Role-based authentication (`role_headers`):** the API enforces
role-based access control that isn't documented in its OpenAPI spec. To
test this, `role_headers("RECEPTIONIST")` (etc.) logs in as any configured
role on demand, with each role's token cached for the whole test run — a
real API rate limit (5 logins/minute) made this caching necessary, not
optional.

## 3. What's Implemented

- **Authentication** — login (positive/negative/parametrized), logout
  (with real session-invalidation verification), password change and
  reset flows (fields discovered via a probe technique, since the API
  spec didn't document them).
- **Patients** — registration (private & HMO, with nested allergies/
  next-of-kin), search (name, partial name, case-insensitivity, MRN),
  profile view/update. Runs as Receptionist — confirmed empirically that
  Admin cannot register patients.
- **Billing** — Invoice CRUD (create/issue/cancel) and HMO claims, *plus*
  a separate suite testing the real clinical billing-clearance gate
  (Doctor opens an Encounter → Biller clears billing → gate opens for
  Lab/Pharmacy), which is the workflow that actually matters clinically.

## 4. Real Findings

**RBAC enforcement undocumented in the API spec.** The OpenAPI schema
marks `POST /api/v1/patients/` as simply requiring authentication — no
role restriction. The first real test run, using an Admin account,
returned `403` on every single call, including plain field-validation
checks that should have been `400`. This confirmed the backend enforces
role-based access the spec never mentions — true of the whole schema, not
just this endpoint. Fix: a `role_headers` fixture factory letting tests
authenticate as any specific role, rather than one fixed account.

**Unsanitized script content stored and echoed by the API.** Submitting
`<script>alert(1)</script>` as a patient's `first_name`/`address` resulted
in the API storing and returning it completely raw and unescaped
(logged as BG-035). Important distinction I deliberately did not overstate:
this confirms *unsafe API-level input handling*, not *confirmed exploitable
XSS* — that would require proving the payload executes when rendered in a
real browser, which needs UI-level automation (Playwright) not yet built.
The test and the bug report both reflect this precise, narrower claim.

**Real environment constraint: a 50-patient plan quota.** Since there's no
DELETE endpoint for patients (deliberate — EMR audit-trail requirements),
and the QA tenant is subject to the same `max_patients` limit as a real
paying customer, continuous registration testing eventually exhausted the
quota. Response was two-layered: at the code level, any fixture that only
needs to *read* an existing patient was rescoped from per-test to
per-module, cutting unnecessary patient creation; at the environment
level, the real fix (a higher-tier or reset-enabled QA tenant) was flagged
as an infrastructure request, not something test code should work around
indefinitely.

**Invoice CRUD alone doesn't test the real billing workflow.** Initial
billing tests covered the Invoice resource in isolation (create, issue,
cancel) — technically correct, but disconnected from the actual clinical
flow described in the roles documentation: Doctor opens an encounter,
Biller must clear billing before the patient can reach Lab/Pharmacy. A
second test suite was built specifically around the real gate endpoints
(`/encounters/{id}/clear-billing/`, `/approve-zero/`), checking the actual
effect (`billing_cleared` flips to `True`) rather than just the response
code — plus an RBAC check confirming a Doctor cannot clear their own
patient's billing.

## 5. How to Run

```bash
cd 07_Automation/API
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in real credentials per role — see conftest.py's ROLE_ENV_MAP

pytest tests/authentication/ -v
pytest tests/patients/ -v
pytest tests/billing/ -v

# Run by marker instead of by folder:
pytest -m smoke
pytest -m "regression and negative"
```

Required `.env` variables follow the pattern `MEDSYNC_<ROLE>_EMAIL` /
`MEDSYNC_<ROLE>_PASSWORD` for each role a test file needs (see
`conftest.py`'s `ROLE_ENV_MAP` for the full list).

## 6. Known Limitations / Not Yet Covered

- **Tenant isolation** (manual `TC-SEARCH-012`, Critical) — needs a second
  tenant's credentials to verify; not yet available.
- **Inactive HMO provider registration** — business rule unconfirmed
  (does it succeed or get blocked?); test explicitly skipped pending
  confirmation, not guessed at.
- **XSS browser-execution proof** — the API-level finding above is
  confirmed; whether it actually executes in MedSync's UI is unverified,
  pending UI/Playwright automation (not yet started).
- **SQL injection coverage is intentionally described as weak evidence,
  not proof of safety** — current checks (including a control-vs-special-
  character comparison) can surface obvious problems (server errors,
  exposed database syntax errors) but cannot fully certify the query layer
  is safe against injection. Full assurance needs code-level review or
  dedicated security tooling.
- **Remaining modules not yet automated:** Consultations, Laboratory,
  Pharmacy, Admissions, Referrals, Users/RBAC as a dedicated suite,
  Offline Sync. `API_TEST_MAPPING.md` has endpoint-level detail ready for
  each.
- **UI automation** has not started (`UI/AUTOMATION_STRATEGY.md` is a
  placeholder). Phases 6–10 of the original plan (test data/fixtures
  refinement, CI/CD via GitHub Actions, HTML reporting) are also pending.

## 7. What I'd Do Next

1. Confirm the two open business rules above (inactive HMO provider,
   zero-item claim submission) with whoever owns the product logic.
2. Build a minimal Playwright check specifically to confirm or rule out
   the XSS finding's real-world exploitability.
3. Continue module-by-module automation in the established priority order
   (Offline Sync next, per the original Risk Register-driven plan).
4. Set up GitHub Actions to run the suite on push, with HTML reporting
   (`pytest-html` is already a dependency).
5. Request either a higher-tier QA tenant plan or a scheduled database
   reset, so continuous testing isn't bottlenecked by a real commercial
   patient quota.
