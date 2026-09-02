# Automation Strategy — MedSync EMR API Test Suite

## 1. Purpose

This document defines what will be automated for MedSync, why, and how automation
fits alongside the manual testing already performed (Requirement Analysis, Risk
Register, Test Plan, and manual Test Cases in `04_Test_Design/`). Automation is not
a replacement for manual/exploratory testing — it exists to catch regressions fast,
free up manual testing time for new features and exploratory work, and provide
repeatable, evidence-backed test execution for CI/CD.

## 2. Scope

### In Scope for Automation

API-level automation using `pytest` + `requests`, covering:

- Authentication (login, token handling, logout, invalid credentials)
- Patients (registration, search, duplicate handling)
- Consultations
- Laboratory
- Pharmacy
- Billing
- Admissions
- Referrals
- HMO
- Users / RBAC
- Offline-related APIs (sync endpoints only — not offline UI behavior)

### Out of Scope for Automation (for now)

- UI-level automation (tracked separately under Playwright, not part of this
  pytest API strategy)
- Performance / load testing
- Security penetration testing
- Third-party integrations unavailable in the test environment
- Purely exploratory or usability-driven testing — this remains manual by nature

## 3. What Will Be Automated vs. What Remains Manual

| Category | Automated | Manual |
|---|---|---|
| Repetitive regression checks (login, CRUD flows) | ✅ | |
| Positive/negative API validation | ✅ | |
| Business-rule edge cases (SQLi, XSS, boundary values) | ✅ | |
| Exploratory testing | | ✅ |
| Usability / visual review | | ✅ |
| One-off investigative bug repro | | ✅ |
| New, unstable, frequently-changing features | | ✅ (until stable, then automate) |

**Rule of thumb:** automate anything we'd otherwise repeat by hand every regression
cycle. Leave anything requiring human judgment (visual correctness, usability,
first-pass exploration of new features) manual.

## 4. Automation Priorities

Priority is driven directly by the Risk Register (see `02_Risk_Assessment/`).
High-risk, high-frequency modules are automated first:

| Priority | Module | Reason |
|---|---|---|
| 1 | Authentication | Foundation — every other test depends on it |
| 2 | Patient Registration | High risk (R-002, score 9) — duplicate/incorrect records |
| 3 | Billing | High risk (R-003, score 9) — HMO vs. Private billing errors |
| 4 | Offline Sync APIs | High risk (R-005, score 9) — data loss/sync failures |
| 5 | Consultations, Laboratory, Pharmacy | Medium risk, core clinical workflow |
| 6 | Admissions, Referrals | Medium/Low risk |
| 7 | Users/RBAC, HMO | Supporting modules, tested after core flows are stable |

## 5. Test Types Covered

- Positive (happy path) tests
- Negative tests (invalid input, missing fields, unauthorized access)
- Boundary value tests (very long strings, min/max values)
- Security-adjacent tests (SQL injection payloads, XSS payloads) — sanitization
  checks only, not full penetration testing
- Business-rule tests (e.g., HMO vs. Private billing logic, tenant isolation)

## 6. Modules / Features to Cover

Mirrors the manual Test Case structure already established:

```
Authentication
Patients (Registration, Search)
Consultations
Laboratory
Pharmacy
Billing
Admissions
Referrals
HMO
Users / Roles (RBAC)
Offline (sync endpoints)
```

## 7. Entry Criteria

- Swagger/API documentation is available for the module being automated
- A stable test environment (QA) is reachable
- Test accounts (Facility Admin, Doctor, Receptionist, Nurse) exist and are
  documented in the Test Data Registry
- The corresponding manual test cases for that module already exist (automation
  follows manual coverage, not the other way around)

## 8. Exit Criteria

- All Priority 1–4 modules (Authentication, Patient Registration, Billing,
  Offline Sync) have automated positive + negative test coverage
- Suite runs cleanly via `pytest -m regression` with no flaky/intermittent
  failures
- CI pipeline (GitHub Actions) executes the suite on push and produces a report
- README documents what is automated, what remains manual, and why

## 9. Relationship to Manual Testing

Automation does not remove the need for the manual artifacts already built:

- Manual Test Cases remain the source of truth for *what* to test
- Automation implements the subset of those cases that are stable, repeatable,
  and regression-worthy
- New defects found manually get a corresponding automated regression test only
  once the underlying feature is confirmed stable (avoids automating against a
  moving target)

## 10. Test Data Policy — No-Delete Resources

Several MedSync resources (confirmed via API_TEST_MAPPING.md) have no DELETE
endpoint — patients are the clearest example, consistent with EMR
audit-trail requirements (records are permanent; deactivation/flags exist
instead of deletion). This has a direct consequence for automated tests:

- **Never hardcode unique-constrained fields** (phone numbers, emails, etc.)
  in a test that creates a record. A fixed value works once, then collides
  with the leftover record on every subsequent run.
- **Generate fresh unique values per test run** instead (see
  `tests/patients/conftest.py`'s `unique_phone` fixture for the pattern).
- **Accept that create-only resources accumulate test data in the QA
  environment over time.** This is normal for a shared QA/staging
  environment, not a flaw in the test suite — periodic manual cleanup of the
  QA database (outside of automated tests) is the appropriate solution if
  volume becomes a problem, not working around it in test code.
- Tests that must prove a *rejection* rule (e.g., "duplicate phone is
  rejected") unavoidably create at least one real record to duplicate
  against — this is accepted as a deliberate, necessary cost, not something
  to eliminate.

### 10.1 Real-World Update: Hit the Plan's Patient Quota

Confirmed in practice, not hypothetical: the QA tenant is subject to the
same `max_patients` plan limit as a real customer (per the `Plan` schema —
Starter-tier caps at 50). Automated registration testing hit this ceiling.

**Two-part response:**
1. **Environment-level (the real fix, outside test code):** request either
   a higher-tier/unlimited plan for the QA tenant specifically, or a
   periodic reset mechanism (nightly/pre-CI) for the QA database. A test
   environment should not be bound by the same commercial constraints as a
   paying customer.
2. **Code-level (within our control, applied now):** any fixture that only
   needs to *read* an existing patient (not test the act of creating one)
   should be scoped broader than `function` — e.g. `scope="module"` — so
   it creates ONE patient shared by every test in that file, not one per
   test. Applied to `registered_patient` in `tests/patients/conftest.py`.
   Tests that ARE testing patient creation itself (Registration's tests)
   cannot be consolidated this way — they inherently consume quota per run,
   which is exactly why the environment-level fix above still matters.

---

*Next: Phase 2 — Project Setup & Architecture (pytest project skeleton).*