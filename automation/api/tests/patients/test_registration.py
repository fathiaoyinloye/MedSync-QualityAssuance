import pytest
import requests


@pytest.mark.smoke
@pytest.mark.critical
def test_register_private_patient_with_required_fields(base_url, auth_headers, unique_phone):
    """
    Positive case using only the fields confirmed required by the schema
    (API_TEST_MAPPING.md): first_name, last_name, dob, sex, phone.
    unique_phone (from the local conftest above) guarantees this succeeds
    on every run, not just the first one.
    """
    payload = {
        "first_name": "Test",
        "last_name": "Patient",
        "dob": "1990-01-01",
        "sex": "M",
        "phone": unique_phone,
        "patient_type": "PRIVATE",
    }
    response = requests.post(f"{base_url}/api/v1/patients/", headers=auth_headers, json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["first_name"] == "Test"
    assert "mrn" in body, "Expected the system to auto-generate a medical record number"


@pytest.mark.regression
@pytest.mark.negative
@pytest.mark.parametrize(
    "missing_field",
    ["first_name", "last_name", "dob", "sex", "phone"],
)
def test_register_patient_missing_required_field(base_url, auth_headers, unique_phone, missing_field):
    """
    One test, run once per required field, each time with that ONE field
    removed. This is safe to run repeatedly — a 400 validation error means
    no patient record actually gets created, so there's nothing to clean up.
    """
    payload = {
        "first_name": "Test",
        "last_name": "Patient",
        "dob": "1990-01-01",
        "sex": "M",
        "phone": unique_phone,
    }
    del payload[missing_field]

    response = requests.post(f"{base_url}/api/v1/patients/", headers=auth_headers, json=payload)
    assert response.status_code == 400, f"Missing '{missing_field}' should have been rejected"


@pytest.mark.critical
def test_register_patient_with_duplicate_phone_is_rejected(base_url, auth_headers, unique_phone):
    """
    Maps to Risk Register R-002/R-015 (duplicate patient records, score 9).

    Unlike every other test above, THIS one necessarily creates a real,
    permanent patient record on success (the first registration) — there's
    no way to test "duplicate phone is rejected" without first having one
    real registered phone to duplicate. Accepted as a known, deliberate cost
    of testing this specific business rule with no delete endpoint available.
    """
    first_payload = {
        "first_name": "Original",
        "last_name": "Patient",
        "dob": "1990-01-01",
        "sex": "M",
        "phone": unique_phone,
    }
    first_response = requests.post(f"{base_url}/api/v1/patients/", headers=auth_headers, json=first_payload)
    assert first_response.status_code == 201

    duplicate_payload = {
        "first_name": "Different",
        "last_name": "Person",
        "dob": "1985-05-05",
        "sex": "F",
        "phone": unique_phone,  # same phone on purpose
    }
    duplicate_response = requests.post(f"{base_url}/api/v1/patients/", headers=auth_headers, json=duplicate_payload)
    assert duplicate_response.status_code == 400, "Duplicate phone number should have been rejected"