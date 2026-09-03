# Location: 07_Automation/API/tests/billing/conftest.py
import pytest
import requests


@pytest.fixture
def biller_headers(role_headers):
    return role_headers("BILLER")


@pytest.fixture(scope="module")
def billing_test_patient(role_headers, base_url):
    """One shared PRIVATE patient for the whole billing test file — billing tests need
    a patient to invoice, they don't need a fresh one per test."""
    import random
    suffix = "".join(random.choices("0123456789", k=6))
    headers = role_headers("RECEPTIONIST")
    payload = {
        "first_name": f"BillingTest{suffix}",
        "last_name": "Patient",
        "dob": "1988-08-08",
        "sex": "M",
        "phone": "081" + suffix + "00",
        "patient_type": "PRIVATE",
    }
    resp = requests.post(f"{base_url}/api/v1/patients/", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
def draft_invoice(biller_headers, base_url, billing_test_patient):
    """A fresh DRAFT invoice for the shared billing_test_patient — function-scoped,
    since most tests need to mutate an invoice's status without affecting others."""
    payload = {"patient": billing_test_patient["id"]}
    resp = requests.post(f"{base_url}/api/v1/billing/invoices/", json=payload, headers=biller_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()