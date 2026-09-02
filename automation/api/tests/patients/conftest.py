import random
import requests
import pytest


@pytest.fixture
def unique_phone():

    return "080" + "".join(random.choices("0123456789", k=8))


@pytest.fixture
def minimal_private_patient(unique_phone):

    return {
        "first_name": "Test",
        "last_name": "Patient",
        "dob": "1990-01-01",
        "sex": "M",
        "phone": unique_phone,
        "patient_type": "PRIVATE",
    }


@pytest.fixture
def active_hmo_provider(auth_headers, base_url):
   
    resp = requests.get(f"{base_url}/api/v1/patients/hmo-providers/", headers=auth_headers)
    resp.raise_for_status()
    body = resp.json()
    results = body.get("results", body) if isinstance(body, dict) else body
    active = [p for p in results if p.get("is_active", True)]
    if not active:
        pytest.skip("No active HMO provider configured in this environment")
    return active[0]


@pytest.fixture
def receptionist_headers(role_headers):
    return role_headers("RECEPTIONIST")