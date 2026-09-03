# Location: 07_Automation/API/tests/billing/test_encounter_billing_clearance.py
"""
Real clinical billing-gate workflow, per MedSync_Roles.md:
Receptionist registers patient -> Doctor opens an Encounter -> Biller
clears billing -> patient is unlocked for Lab/Pharmacy.

This is DIFFERENT from test_invoices.py (which tests the Invoice resource
in isolation) — this tests the actual gate that controls whether a
patient's care can proceed, which is the real-world thing Billing exists
to enforce.
"""
import pytest
import requests


@pytest.fixture
def doctor_headers(role_headers):
    return role_headers("DOCTOR")


@pytest.fixture
def open_encounter(role_headers, doctor_headers, base_url):
    """Registers a fresh patient, then opens a real Encounter for them as Doctor."""
    import random
    suffix = "".join(random.choices("0123456789", k=6))
    receptionist = role_headers("RECEPTIONIST")
    patient_resp = requests.post(
        f"{base_url}/api/v1/patients/",
        json={
            "first_name": f"EncounterTest{suffix}",
            "last_name": "Patient",
            "dob": "1990-06-06",
            "sex": "M",
            "phone": "083" + suffix + "00",
            "patient_type": "PRIVATE",
        },
        headers=receptionist,
    )
    assert patient_resp.status_code == 201, patient_resp.text

    encounter_resp = requests.post(
        f"{base_url}/api/v1/encounters/",
        json={"patient": patient_resp.json()["id"], "encounter_type": "OPD"},
        headers=doctor_headers,
    )
    assert encounter_resp.status_code == 201, encounter_resp.text
    return encounter_resp.json()


@pytest.mark.critical
def test_new_encounter_starts_billing_uncleared(base_url, doctor_headers, open_encounter):
    """A fresh encounter should NOT already be billing-cleared — the gate must start closed."""
    resp = requests.get(f"{base_url}/api/v1/encounters/{open_encounter['id']}/", headers=doctor_headers)
    assert resp.status_code == 200
    assert resp.json()["billing_cleared"] is False, "New encounter should not start pre-cleared"


@pytest.mark.critical
def test_biller_clears_billing_and_gate_opens(base_url, biller_headers, open_encounter):
    """
    The real gate test: after Biller clears billing, the encounter's
    billing_cleared flag must flip to True — checking the EFFECT, not just
    that the call returned 200 (same principle as the logout test).
    """
    clear_resp = requests.post(
        f"{base_url}/api/v1/encounters/{open_encounter['id']}/clear-billing/",
        headers=biller_headers,
    )
    assert clear_resp.status_code == 200, clear_resp.text

    check_resp = requests.get(f"{base_url}/api/v1/encounters/{open_encounter['id']}/", headers=biller_headers)
    assert check_resp.json()["billing_cleared"] is True, "Gate should be open after Biller clears billing"


@pytest.mark.critical
def test_biller_can_zero_clear_for_emergency(base_url, biller_headers, open_encounter):
    """
    approve-zero: Biller-only emergency/pay-later clearance, distinct from
    a real payment. Per API_TEST_MAPPING.md, this unlocks Lab/Pharmacy
    WITHOUT payment — a different mechanism than clear-billing above.
    """
    resp = requests.post(
        f"{base_url}/api/v1/encounters/{open_encounter['id']}/approve-zero/",
        headers=biller_headers,
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.regression
@pytest.mark.negative
def test_non_biller_cannot_clear_billing(base_url, doctor_headers, open_encounter):
    """
    RBAC check: Doctor should NOT be able to clear their own patient's
    billing gate — that's specifically Biller's job per the roles doc.
    """
    resp = requests.post(
        f"{base_url}/api/v1/encounters/{open_encounter['id']}/clear-billing/",
        headers=doctor_headers,
    )
    assert resp.status_code == 403, (
        f"Expected Doctor to be denied clearing billing, got {resp.status_code}: {resp.text}"
    )