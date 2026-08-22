# Test Automation Strategy — MedSync EMR (Overview)

This is the top-level automation strategy for MedSync. It defines the overall
philosophy, layer ownership, and CI cadence. Layer-specific implementation
detail lives in each framework's own strategy document:

- **API layer detail:** [`API/AUTOMATION_STRATEGY.md`](../API/AUTOMATION_STRATEGY.md)
- **UI layer detail:** `UI/AUTOMATION_STRATEGY.md` *(written when Playwright work begins)*

## 1. Why We Split Strategy by Layer

API and UI automation differ in speed, stability, tooling, and how often they
run — treating them as one undifferentiated "automation strategy" hides those
differences. Each layer gets its own detailed document; this file explains how
they relate to each other and to manual testing.

## 2. Test Pyramid Philosophy

```
        ▲
       /UI\        Few tests — slow, higher flake risk, expensive to maintain
      /-----\       Tool: Playwright
     / API   \      Bulk of automated coverage — fast, stable
    /---------\      Tool: pytest + requests
   /  Manual   \    Exploratory, usability, new/unstable features
  /-------------\    Owner: QA (this project)
```

MedSync does not currently have a dedicated unit-testing layer under QA
ownership (that's developer-owned), so our automation pyramid for this project
has two QA-owned layers: API (broad) and UI (narrow, selective).

**Target ratio:** roughly 80% API / 20% UI for automated coverage. UI
automation is reserved for a small number of true end-to-end business
journeys (e.g., "receptionist registers a patient through the real UI,
start to finish") rather than duplicating every API test at the UI level.

## 3. Layer Responsibilities

| Layer | Tool | What it covers | Run cadence |
|---|---|---|---|
| API | pytest + requests | Business logic, validation, positive/negative/boundary cases, security-adjacent input handling | Every push (CI) |
| UI | Playwright | Critical end-to-end user journeys only | Nightly / pre-release |
| Manual | — | Exploratory testing, usability, new/unstable features, one-off bug repro | Ongoing, ad hoc |

## 4. Relationship to Manual Testing

Manual Test Cases (`04_Test_Design/`) remain the source of truth for *what*
should be tested. Automation — at either layer — implements the subset that is
stable, repeatable, and worth protecting against regression. New defects found
manually only get an automated regression test once the underlying feature is
confirmed stable.

## 5. Ownership

For this project, one QA/SDET engineer owns both layers. In a larger team,
API automation is typically owned by QA/SDET and UI automation is sometimes
shared with frontend developers, since UI test stability often depends on how
testable the frontend markup is.

## 6. Status

| Document | Status |
|---|---|
| This overview | Complete |
| `API/AUTOMATION_STRATEGY.md` | Complete (Phase 1) |
| `UI/AUTOMATION_STRATEGY.md` | Not started — deferred to when Playwright work begins |
