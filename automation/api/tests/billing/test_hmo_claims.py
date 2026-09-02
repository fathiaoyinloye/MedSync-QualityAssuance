# Location: 07_Automation/API/tests/billing/test_hmo_claims.py
"""
HMO Claims tests — the other half of R-003. Runs as HMO_DESK/BILLER per
MedSync_Roles.md. Uses an HMO invoice, since claims attach to invoices.
"""
import pytest
import requests


@pytest.fixture
def hmo_desk_headers(role_headers):
    return role_headers("HMO_DESK")


@pytest.fixture
def hmo_invoice(biller_headers, base_url, role_headers):
    """A DRAFT invoice for an HMO patient, as the base for claim tests."""
    import random
    suffix = "".join(random.choices("0123456789", k=6))
    receptionist = role_headers("RECEPTIONIST")
    patient_resp = requests.post(
        f"{base_url}/api/v1/patients/",
        json={
            "first_name": f"HmoBilling{suffix}",
            "last_name": "Patient",
            "dob": "1980-01-01",
            "sex": "F",
            "phone": "082" + suffix + "00",
            "patient_type": "HMO",
        },
        headers=receptionist,
    )
    patient_resp.raise_for_status()
    invoice_resp = requests.post(
        f"{base_url}/api/v1/billing/invoices/",
        json={"patient": patient_resp.json()["id"]},
        headers=biller_headers,
    )
    invoice_resp.raise_for_status()
    return invoice_resp.json()


@pytest.mark.critical
def test_create_hmo_claim_for_invoice(base_url, biller_headers, hmo_invoice):
    payload = {
        "invoice": hmo_invoice["id"],
        "hmo_name": "Hygeia",
        "member_number": "MEM-TEST-001",
    }
    resp = requests.post(f"{base_url}/api/v1/billing/claims/", json=payload, headers=biller_headers)
    assert resp.status_code == 201, resp.text


@pytest.mark.negative
def test_submit_claim_with_zero_items_status(base_url, biller_headers, hmo_invoice):
    """
    Open question flagged in API_TEST_MAPPING.md: should submitting a claim
    with zero items be blocked? We assert it's at least handled without a
    server error — tightening this assertion once the real business rule
    is confirmed either way.
    """
    claim_resp = requests.post(
        f"{base_url}/api/v1/billing/claims/",
        json={"invoice": hmo_invoice["id"], "hmo_name": "Hygeia", "member_number": "MEM-TEST-002"},
        headers=biller_headers,
    )
    claim_id = claim_resp.json()["id"]

    submit_resp = requests.post(f"{base_url}/api/v1/billing/claims/{claim_id}/submit/", headers=biller_headers)
    assert submit_resp.status_code in (200, 400), (
        f"Unexpected server behavior submitting a zero-item claim: {submit_resp.status_code}"
    )