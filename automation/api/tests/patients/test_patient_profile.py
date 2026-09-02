# Location: 07_Automation/API/tests/patients/test_patient_profile.py
"""
Patient Profile tests — GET/PUT/PATCH /api/v1/patients/{id}/
"""
import pytest
import requests

PATIENTS_URL = "/api/v1/patients/"


@pytest.mark.smoke
def test_get_patient_by_id_returns_correct_record(base_url, receptionist_headers, registered_patient):
    response = requests.get(f"{base_url}{PATIENTS_URL}{registered_patient['id']}/", headers=receptionist_headers)
    assert response.status_code == 200
    assert response.json()["id"] == registered_patient["id"]


def test_update_patient_phone_number(base_url, receptionist_headers, registered_patient, unique_phone):
    response = requests.patch(
        f"{base_url}{PATIENTS_URL}{registered_patient['id']}/",
        json={"phone": unique_phone},
        headers=receptionist_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["phone"] == unique_phone


@pytest.mark.negative
def test_get_nonexistent_patient_returns_404(base_url, receptionist_headers):
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = requests.get(f"{base_url}{PATIENTS_URL}{fake_id}/", headers=receptionist_headers)
    assert response.status_code == 404, response.text


@pytest.mark.negative
def test_update_patient_with_invalid_sex_value_returns_400(base_url, receptionist_headers, registered_patient):
    response = requests.patch(
        f"{base_url}{PATIENTS_URL}{registered_patient['id']}/",
        json={"sex": "X"},
        headers=receptionist_headers,
    )
    assert response.status_code == 400, response.text