# Location: 07_Automation/API/tests/patients/conftest.py

import random
import pytest
import requests


@pytest.fixture
def receptionist_headers(role_headers):
    """
    Small named convenience wrapper around role_headers("RECEPTIONIST") — so
    test functions can just ask for receptionist_headers directly, matching
    the readability of the original single-role auth_headers fixture,
    instead of every test writing role_headers("RECEPTIONIST") by hand.
    """
    return role_headers("RECEPTIONIST")


@pytest.fixture
def unique_phone():
    """
    Generates a fresh phone number every time a test asks for it.

    Why this exists: there's no delete-patient endpoint in this API (patient
    records are permanent, matching real EMR audit-trail requirements — see
    API_TEST_MAPPING.md). A hardcoded phone number would work once, then
    collide with the leftover record on every run after that.

    NOTE: this file previously lived merged into the root conftest.py
    without `import random` at all — that would have crashed the moment
    any test actually used this fixture. Fixed here.
    """
    return "080" + "".join(random.choices("0123456789", k=8))


@pytest.fixture
def minimal_private_patient(unique_phone):
    """Smallest valid payload for a PRIVATE patient registration."""
    return {
        "first_name": "Test",
        "last_name": "Patient",
        "dob": "1990-01-01",
        "sex": "M",
        "phone": unique_phone,
        "patient_type": "PRIVATE",
    }


@pytest.fixture
def active_hmo_provider(receptionist_headers, base_url):
    """
    Fetches a real, active HMO provider from the facility's own catalogue
    instead of hardcoding an ID (per-facility data — an ID valid in one
    environment may not exist in another). Uses receptionist_headers since
    the roles doc confirms Receptionist can read this list (needed for
    registration); previously used Admin, which also works, but Receptionist
    is the more accurate actor for this specific read.
    """
    response = requests.get(f"{base_url}/api/v1/patients/hmo-providers/", headers=receptionist_headers)
    response.raise_for_status()
    body = response.json()
    results = body.get("results", body) if isinstance(body, dict) else body
    active = [p for p in results if p.get("is_active", True)]
    if not active:
        pytest.skip("No active HMO provider configured in this environment")
    return active[0]


@pytest.fixture(scope="module")
def registered_patient(role_headers, base_url):
   
    import random
    suffix = "".join(random.choices("0123456789", k=6))
    headers = role_headers("RECEPTIONIST")
    payload = {
        "first_name": f"SearchTest{suffix}",
        "last_name": "Findable",
        "dob": "1992-02-02",
        "sex": "F",
        "phone": "080" + suffix + "00",
        "patient_type": "PRIVATE",
    }
    response = requests.post(f"{base_url}/api/v1/patients/", json=payload, headers=headers)
    response.raise_for_status()
    return response.json()