# API Test Mapping — MedSync EMR

Source: `https://lafia.api.medsync.com.ng/api/schema/swagger-ui/` (OpenAPI 3.0.3,
fetched for Phase 3). All endpoints are JWT-authenticated (`jwtAuth`) unless
explicitly marked public.

Depth follows automation priority (see `AUTOMATION_STRATEGY.md`): Priority 1–4
modules are mapped in full; the rest are inventoried now and will be detailed
immediately before their automation phase begins, to avoid mapping detail that
goes stale before it's used.

---

## Priority 1 — Authentication (`/api/v1/auth/`)

| Endpoint | Method | Auth | Notes |
|---|---|---|---|
| `/api/v1/auth/token/` | POST | Public | Login. **Rate-limited: 5 attempts/min per IP.** Refresh token returned as httpOnly cookie, not JSON body — only `access` comes back in the response. |
| `/api/v1/auth/token/refresh/` | POST | Public (reads cookie) | Reads refresh token from httpOnly cookie only, never the request body. Rotates + blacklists the old token on every call. |
| `/api/v1/auth/logout/` | POST | Auth | Blacklists the refresh token (from cookie) and clears it. |
| `/api/v1/auth/me/` | GET | Auth | Current user profile. |
| `/api/v1/auth/change-password/` | POST | Auth | Logged-in user changes their own password (needs old password). |
| `/api/v1/auth/request-password-reset/` | POST | Public | "Forgot password" — always returns the same generic response whether or not the email exists (prevents email enumeration). Also flags the account for Facility Admin-driven reset. |
| `/api/v1/auth/password-reset/confirm/` | POST | Public | Second leg of emailed reset; token self-invalidates on success (single-use). |

**Positive scenarios:**
- Valid login → 200 + access token
- Token refresh with valid cookie → new access + rotated refresh cookie
- Logout → refresh token blacklisted, subsequent refresh attempt fails
- Password reset full flow (request → confirm) → can log in with new password

**Negative scenarios:**
- Invalid credentials → login denied, no user enumeration in error message
- 6th login attempt within a minute → rate-limited (test the 5/min boundary specifically)
- Refresh call with expired/blacklisted token → rejected
- Password reset request for a non-existent email → **same generic response** as a real one (this is a specific thing to assert, not just "doesn't error")
- Reused password-reset token (second confirm attempt) → rejected, self-invalidated

**Business rule to test explicitly:** the refresh token never appears in any JSON response body — verify this directly (a real security-relevant assertion, not just "login works").

---

## Priority 2 — Patients (`/api/v1/patients/`)

| Endpoint | Method | Auth | Notes |
|---|---|---|---|
| `/api/v1/patients/` | GET, POST | Auth | List (search/ordering/paginated) + register. POST accepts nested `allergies`, `insurance_cards`, `next_of_kin` at registration time. |
| `/api/v1/patients/{id}/` | GET, PUT, PATCH | Auth | Detail/edit. Note: allergies/insurance/next-of-kin are **read-only** here — only editable via registration or their own dedicated endpoints. |
| `/api/v1/patients/{patient_id}/allergies/` | GET, POST | Auth | |
| `/api/v1/patients/{patient_id}/conditions/` | GET, POST | Auth | Condition types include HIV, Hepatitis B/C, Sickle Cell, PUD, Other. |
| `/api/v1/patients/{patient_id}/coverage-check/` | POST | Auth | Records the *answer* an HMO insurer gave when asked about coverage — the system does not compute coverage itself. Body: `outcome` (ACTIVE/LAPSED/NOT_FOUND). |
| `/api/v1/patients/hmo-providers/` | GET, POST | Auth | Facility's HMO catalogue. Read open to anyone who registers/bills; write restricted. `?all=true` includes inactive providers. |
| `/api/v1/patients/icd-codes/` | GET, POST | Auth | Diagnosis catalogue (ICD-10/11 + doctor-added "LOCAL" entries). |

**Required fields on registration** (`PatientRegistrationRequest`): `first_name`, `last_name`, `dob`, `sex`, `phone`. `patient_type` is `PRIVATE` or `HMO`.

**Positive scenarios:**
- Register PRIVATE patient with only required fields → 201, MRN auto-generated
- Register HMO patient with `hmo_provider` + `hmo_member_number` → 201
- Register with nested allergies/insurance/next-of-kin in one call → all nested objects created
- Search patient by name/MRN → correct match returned

**Negative scenarios:**
- Missing required field (first_name, last_name, dob, sex, phone) → 400 with field-level validation
- Register HMO patient with inactive `hmo_provider` → should this succeed or be blocked? (verify actual business rule — not stated in spec description, needs manual confirmation)
- `sex` outside `M/F/O` enum → 400
- SQL injection / XSS payloads in `first_name`/`address` → sanitized, not executed/stored raw

**This directly maps to your existing manual `TC-PAT-*` test cases** — automation should implement the stable subset (required-field validation, duplicate handling) rather than duplicate all 35 manual cases.

---

## Priority 3 — Billing (`/api/v1/billing/`)

This is the largest and most business-rule-dense module. Splits into: **Invoices** (cash/private), **HMO Claims**, **Payments**, **Price Lists/Tariffs**, **Reports**.

| Endpoint | Method | Auth | Notes |
|---|---|---|---|
| `/api/v1/billing/invoices/` | GET, POST | Auth | Filterable by `status`, `payment_mode`, `patient`, `encounter`. |
| `/api/v1/billing/invoices/{id}/` | GET, PUT, PATCH | Auth | |
| `/api/v1/billing/invoices/{id}/issue/` | POST | Auth | DRAFT → ISSUED |
| `/api/v1/billing/invoices/{id}/pay/` | POST | Auth | Records payment |
| `/api/v1/billing/invoices/{id}/waive/` | POST | Auth | Facility-Admin-only permanent discount (distinct from zero-clearance below) |
| `/api/v1/billing/invoices/{id}/cancel/` | POST | Auth | |
| `/api/v1/billing/invoices/summary/` | GET | Auth | **Server-side aggregate — must not be computed client-side** (paginated list would silently under-report; Decimal-as-string fields would string-concatenate instead of sum). This is a good target for a dedicated correctness test. |
| `/api/v1/billing/claims/` | GET | Auth | HMO claims list |
| `/api/v1/billing/claims/{id}/` | GET, PUT, PATCH | Auth | |
| `/api/v1/billing/claims/{id}/submit/` | POST | Auth | Marks SUBMITTED, recalculates `amount_claimed` from items |
| `/api/v1/billing/claims/{id}/approve-all/` | POST | Auth | Bulk-approves every PENDING item at listed price |
| `/api/v1/billing/claims/{id}/appeal/` | POST | Auth | |
| `/api/v1/billing/claim-items/{id}/review/` | POST | Auth | Per-line approve/reject with optional negotiated price. Body: `{decision: "APPROVED"|"REJECTED", approved_amount?, authorization_code?, comment?}` |
| `/api/v1/billing/hmo-tariffs/` | GET, POST | Auth | What each insurer agreed to pay. Managed by biller/facility admin only — "getting it wrong misprices every claim built from it." |
| `/api/v1/billing/hmo-tariffs/import/` | POST | Auth | Bulk CSV import. **Rows validated individually — a 400-row file with 2 bad rows imports 398, reports the 2.** Good negative-test target: verify partial success, not all-or-nothing failure. |
| `/api/v1/billing/payments/` | GET | Auth | Flat payment ledger |
| `/api/v1/encounters/{id}/approve-zero/` | POST | Auth | Biller-only zero-Naira clearance for emergency/pay-later — unlocks Lab/Pharmacy without payment |
| `/api/v1/encounters/{id}/pre-approve/` | POST | Auth | **PRIVATE only** — HMO encounters are never billing-gated in the first place, so this doesn't apply to them. Payment still due, just deferred. |

**This is where your Risk Register's R-003 (HMO vs. Private billed incorrectly, score 9) lives.** Priority automation targets:

**Positive scenarios:**
- PRIVATE invoice: create → issue → pay → status becomes FULLY_PAID
- HMO claim: create → add items → submit → `amount_claimed` recalculated correctly
- `approve-all` on a claim with 3 PENDING items → all 3 become APPROVED at listed price
- `invoices/summary` total matches manual sum of all invoice totals (correctness check)

**Negative scenarios — directly tests R-003:**
- HMO patient's encounter routed through a PRIVATE-only endpoint (`pre-approve`) → should reject or behave per spec (verify: spec says PRIVATE only)
- Submit a claim with zero items → should this be blocked?
- `claim-items/review` with `decision` outside APPROVED/REJECTED → 400
- HMO tariff import with 2 bad rows in a 400-row CSV → 398 succeed, 2 reported individually (not all-or-nothing failure)
- Waive an already-CANCELLED invoice → should be rejected

---

## Priority 4 — Offline / Sync (`/api/v1/sync/`)

| Endpoint | Method | Auth | Notes |
|---|---|---|---|
| `/api/v1/sync/pull/` | GET | Auth | Returns "today's working set," delta'd against the client's cursor, **scoped to the user's role.** Spec explicitly notes a past bug here: wrong cursor field + no scoping meant a naive implementation could ship the entire patient database to every device. |
| `/api/v1/sync/push/` | POST | Auth | Receives a batch of offline operations from a device coming back online. |
| `/api/v1/sync/status/` | GET | Auth | |

**This directly maps to Risk Register R-005 (offline sync data loss, score 9).**

**Positive scenarios:**
- Pull with no prior cursor → returns full scoped working set
- Pull with a valid cursor → returns only the delta since that cursor
- Push a valid offline operation batch → applied correctly, reflected in subsequent pull

**Negative/critical scenarios — this is the highest-value area to automate given the documented bug history:**
- **Role scoping:** pull as Receptionist vs. pull as Doctor → verify each gets only their role-appropriate working set, never the full patient database
- **Cursor correctness:** verify the delta cursor is filtered on the correct field (spec explicitly says this was wrong before — a regression test here has real historical justification)
- Push a batch with a conflicting/duplicate operation (e.g., patient already registered by another device) → verify conflict handling, not silent overwrite or duplication
- Push while offline cursor is stale/invalid → graceful rejection, not data corruption

---

## Priority 5 — Consultations / Clinical (`/api/v1/clinical/`, `/api/v1/encounters/`)

Endpoint inventory (full scenario mapping deferred to Phase 5.3 — Consultations):

- `/api/v1/encounters/` (GET, POST), `/api/v1/encounters/{id}/` (GET, PATCH)
- `/api/v1/encounters/{id}/claim/` — doctor picks up an encounter (idempotent — first claim wins)
- `/api/v1/encounters/{id}/finalise/`, `/api/v1/encounters/{id}/timeline/`
- `/api/v1/clinical/vitals/` (POST), `/api/v1/clinical/vitals/history/` (GET)
- `/api/v1/clinical/diagnoses/` (POST), `/api/v1/clinical/diagnoses/{id}/` (GET/PUT/PATCH/DELETE — doctor-only, encounter must still be open)
- `/api/v1/clinical/notes/` (POST), `/api/v1/clinical/notes/{id}/finalise/`, `/api/v1/clinical/notes/{id}/addendum/`
- `/api/v1/clinical/icd-search/`

**Notable business rule:** a Diagnosis can be hard-deleted (no downstream FK depends on it), unlike a Prescription, which needs soft-cancel — worth remembering when writing delete tests for either.

---

## Priority 5 — Laboratory (`/api/v1/lab/`)

- `/api/v1/lab/orders/` (GET, POST), `/api/v1/lab/orders/{id}/` (GET)
- `/api/v1/lab/orders/{id}/collect/`, `/cancel/`, `/confirm-payment/`
- `/api/v1/lab/results/` (POST), `/api/v1/lab/results/{id}/verify/`
- `/api/v1/lab/tests/` (GET, POST) — has `hmo_approval_status`, `priority` (ROUTINE/URGENT/STAT), `requires_payment` filters worth testing against

## Priority 5 — Pharmacy (`/api/v1/pharmacy/`)

- `/api/v1/pharmacy/prescriptions/` (GET, POST), `/{id}/approve/`, `/cancel/`, `/confirm-payment/`
- `/api/v1/pharmacy/prescription-items/{id}/close-short/` — closes a line at whatever was actually dispensed (replaces an old buggy `mark_item_fulfilled` per the spec's own description — worth a regression test given it names a prior bug)
- `/api/v1/pharmacy/prescription-items/{id}/substitute/`
- `/api/v1/pharmacy/dispense/`, `/api/v1/pharmacy/batches/`, `/api/v1/pharmacy/drugs/`
- `/api/v1/pharmacy/requisitions/` — Store Keeper restock workflow
# Priority 5 update

Replaces the "endpoint inventory, full mapping deferred" placeholders for
Consultations/Clinical, Laboratory, and Pharmacy, now that the full OpenAPI
schema is available. Same caveat applies everywhere below as it did for
Patients: **the schema documents field shape, never role permission.**
`security: [jwtAuth: []]` on an endpoint means "must be logged in," nothing
more — it does not mean "any logged-in role may call this." Every POST/action
endpoint below needs the same discover-then-assert RBAC treatment
test_registration_rbac.py established for patient registration before we
trust who can actually call it.

---

## Encounters (`/api/v1/encounters/`)

| Endpoint | Required fields | Notes |
|---|---|---|
| POST `/api/v1/encounters/` | `patient` only | `encounter_type` (OPD/IPD/EMERGENCY/PROCEDURE), `status`, `chief_complaint`, `appointment` all optional |
| POST `/{id}/claim/` | — | Doctor picks up an encounter; **idempotent** — a second claim by anyone is a no-op, first claim wins. Good idempotency test target. |
| POST `/{id}/finalise/` | — | |
| GET `/{id}/timeline/` | — | Chronological summary of all clinical events |
| POST `/{id}/approve-zero/` | — | Biller-only zero-Naira clearance (emergency/pay-later) — unlocks Lab/Pharmacy without payment |
| POST `/{id}/pre-approve/` | — | **PRIVATE only**, idempotent, optional reason note. Payment still due, just deferred — distinct from approve-zero's waiver |
| POST `/{id}/clear-billing/` | — | **Newly surfaced by the full schema — not in the original inventory.** No description given; needs investigation before Phase 5.3 tests are written against it |
| POST `/{id}/clear-hmo/` | — | **Newly surfaced, same as above** — undocumented purpose, needs investigation |

`EncounterDetail` exposes the gating fields flow tests will assert on:
`billing_cleared`, `billing_cleared_zero`, `hmo_cleared`, `pre_approved` —
these are the fields that prove R-003 (HMO vs Private billing) is actually
enforced end-to-end.

## Vitals (`/api/v1/clinical/vitals/`)

- POST `/api/v1/clinical/vitals/` — **only `encounter` is required.** Every
  clinical field (bp_systolic, bp_diastolic, pulse, temperature, spo2,
  respiratory_rate, weight_kg, height_cm, muac) is optional. Worth a
  deliberate test: does a vitals record with zero actual vitals get accepted?
  If so, that's a real gap worth flagging, not just an oversight in our test.
- GET `/history/` — filterable by `encounter` or `patient`, newest first.

## Diagnoses (`/api/v1/clinical/diagnoses/`)

- POST — required: `encounter`, `icd_code`. Optional: `icd_version`
  (ICD10/ICD11), `free_text`, `status` (WORKING/CONFIRMED/QUERIED/RULED_OUT),
  `is_primary`.
- GET/PUT/PATCH/DELETE by id — **doctor-only, encounter must still be open**
  (per the schema's own description). Confirms the earlier note: a Diagnosis
  can be hard-deleted (no downstream FK), unlike a Prescription.

## Clinical Notes (`/api/v1/clinical/notes/`)

- POST — required: `encounter`, `note_type` (HISTORY/EXAMINATION/ASSESSMENT/
  PLAN/PROGRESS/DISCHARGE). **`content` is NOT marked required** in the
  schema — worth a negative test: can a note be created with empty content?
- `/finalise/`, `/addendum/` — no fields documented beyond the path id.

## Referrals (`/api/v1/clinical/referrals/`)

- POST — required: `encounter`, `reason`. `route` enum is INTERNAL (another
  department) vs EXTERNAL (another facility) — confirmed as its own field,
  worth the two separate positive tests already planned.
- Actions: `/accept/`, `/decline/`, `/complete/`, `/cancel/`,
  `/authorise-hmo/`, `/clear-billing/`, `/letter.pdf`.

## Laboratory (`/api/v1/lab/`)

- POST `/api/v1/lab/orders/` — **the schema lists NO required fields at all**
  for `LabOrderRequest` (patient, encounter, priority, clinical_info,
  test_ids are all shown as optional). That's almost certainly an
  under-annotated schema rather than the real behavior — a lab order with no
  patient and no tests shouldn't be creatable. Treat this as a hypothesis to
  test, not a confirmed fact: send a minimal/empty body and see what actually
  comes back before writing the "required field" negative tests here.
- Actions: `/collect/`, `/cancel/`, `/confirm-payment/`.
- POST `/api/v1/lab/results/` — required: `lab_order_item` only.
- `/results/{id}/verify/` — no fields beyond path id.
- Useful filters confirmed on `/lab/orders/`: `hmo_approval_status`,
  `priority` (ROUTINE/URGENT/STAT), `requires_payment`,
  `ready_for_collection`, `payment_pending` — good candidates for filter
  correctness tests later.

## Pharmacy (`/api/v1/pharmacy/`)

- POST `/api/v1/pharmacy/prescriptions/` — required: `encounter`, `items`
  (array). Each item (`PrescriptionItemWriteRequest`) requires `dose` and
  `quantity_prescribed`; `drug` is nullable (supports non-formulary drugs via
  `non_formulary_name`).
- `/{id}/approve/` — pharmacist review step; optional body lets pharmacy
  supply less than prescribed per line (`quantity_to_supply`,
  `shortfall_reason`); no body = approve everything at prescribed quantity.
  **Runs before the money gate on purpose** (schema's own description) — a
  real business rule worth its own test: billing must price what pharmacy
  can actually supply, not what the doctor originally ordered.
- `/{id}/cancel/`, `/{id}/confirm-payment/`.
- `/prescription-items/{id}/close-short/` — replaces a documented prior bug
  (`mark_item_fulfilled` falsely marking non-stocked drugs as dispensed) —
  confirmed regression-test target, as already flagged.
- `/prescription-items/{id}/substitute/`.

---

*Still deferred: Admissions, Referrals-detail-edge-cases, Users/RBAC,
Appointments/Workflow (now fully documented in the schema but still out of
the original 10-module scope — revisit that scoping decision now that we can
see they're fully-built modules, not stubs).*

## Priority 6 — Admissions (`/api/v1/admissions/`)

- `/api/v1/admissions/` (GET, POST), `/{id}/assign-bed/`, `/discharge/`, `/set-daily-rate/`
- `/api/v1/admissions/wards/`, `/api/v1/admissions/beds/`
- `/api/v1/admissions/{id}/nursing-notes/`, `/observations/`, `/drug-administrations/`
- **Business rule to note:** `days_so_far` increments daily while ACTIVE, freezes at discharge — a good target for a time-dependent test once this phase begins.

## Priority 6 — Referrals (`/api/v1/clinical/referrals/`)

- `/api/v1/clinical/referrals/` (GET, POST), `/{id}/accept/`, `/decline/`, `/complete/`, `/cancel/`, `/authorise-hmo/`, `/clear-billing/`
- `route`: INTERNAL (another department) vs. EXTERNAL (another facility) — distinct workflows worth separate positive tests

## Priority 7 — Users / RBAC (`/api/v1/admin/`)

- `/api/v1/admin/users/` (GET, POST), `/{id}/` (GET/PUT/PATCH), `/change-role/`, `/deactivate/`, `/reactivate/`, `/reset-password/`
- `/api/v1/admin/roles/` — readable by any authenticated staff (needed for the Facility Admin's role picker UI), not sensitive
- Roles enum: SUPER_ADMIN, FACILITY_ADMIN, DOCTOR, NURSE, PHARMACIST, STORE_KEEPER, LAB_TECH, RECEPTIONIST, BILLER, HMO_DESK, VIEWER — this maps directly to your RBAC manual test cases

## Priority 7 — HMO (spread across Billing + Patients modules above)

No separate top-level HMO module in the API — HMO functionality lives inside `billing/claims`, `billing/hmo-tariffs`, and `patients/hmo-providers`, already mapped above.

---

## Discovered but Out of Scope (not in original 10-module plan)

Present in the live API, not previously scoped — flagging for a decision:

- **Appointments** (`/api/v1/appointments/`) — booking, scheduling, walk-in queue
- **Workflow/Queue** (`/api/v1/workflow/`) — department routing, check-in
- **Chat** (`/api/v1/chat/`) — internal staff messaging
- **Notifications** (`/api/v1/notifications/`)
- **Analytics** (`/api/v1/analytics/`) — dashboard, disease burden
- **Facility Branding** (`/api/v1/facility/branding/`) — public, unauthenticated
- **Subscriptions** (`/api/v1/subscriptions/`) — tenant plan/billing (SaaS-level, not hospital-level billing)
- **FHIR** (`/fhir/R4/`) — standards-compliance interop endpoints

**Recommendation:** leave these out of the automation strategy for now — none carry a Risk Register score, and adding them would dilute focus from the four scored-High priorities. Revisit after Priority 1–4 automation is complete.

---

*Next: Phase 4 — Authentication & Test Foundation (real fixtures + first working test suite against `/api/v1/auth/token/`).*
