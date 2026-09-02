# Location: 07_Automation/API/tests/patients/test_registration.py
"""
Patient Registration tests — Priority 2 (see API_TEST_MAPPING.md).

Runs as RECEPTIONIST (via receptionist_headers). CONFIRMED by real test
run: Receptionist can register patients; Admin cannot (403). This resolves
the RBAC question that originally blocked this module.
"""
import pytest
import requests

PATIENTS_URL = "/api/v1/patients/"


@pytest.mark.regression
class TestPatientRegistrationPositive:

    def test_register_private_patient_minimal_fields(self, base_url, receptionist_headers, minimal_private_patient):
        resp = requests.post(f"{base_url}{PATIENTS_URL}", json=minimal_private_patient, headers=receptionist_headers)
        assert resp.status_code == 201, resp.text
        assert resp.json().get("mrn"), "Expected an auto-generated MRN on successful registration"

    def test_register_hmo_patient(self, base_url, receptionist_headers, unique_phone, active_hmo_provider):
        """
        FIXED from first run: HMO registration needs a nested insurance_cards
        entry with a policy_number — not just hmo_provider/hmo_member_number
        at the top level. Real error from the API: "Policy number is
        required for HMO patients." This is an undocumented business rule
        (nothing in the schema flags insurance_cards as conditionally
        required) — worth adding to API_TEST_MAPPING.md.
        """
        payload = {
            "first_name": "Hmo",
            "last_name": "Patient",
            "dob": "1985-05-05",
            "sex": "F",
            "phone": unique_phone,
            "patient_type": "HMO",
            "hmo_provider": active_hmo_provider["id"],
            "hmo_member_number": "MEM-" + unique_phone[-6:],
            "insurance_cards": [{
                "hmo_name": active_hmo_provider["name"],
                "member_number": "MEM-" + unique_phone[-6:],
                "policy_number": "POL-" + unique_phone[-6:],
            }],
        }
        resp = requests.post(f"{base_url}{PATIENTS_URL}", json=payload, headers=receptionist_headers)
        assert resp.status_code == 201, resp.text
        assert resp.json().get("mrn")

    def test_register_with_nested_objects(self, base_url, receptionist_headers, unique_phone):
        """
        FIXED from first run: allergies requires 'severity' (schema-required,
        I omitted it); next_of_kin.relationship enum is UPPERCASE ("SPOUSE"),
        not title-case ("Spouse") — case-sensitive exact match.
        """
        payload = {
            "first_name": "Nested",
            "last_name": "Objects",
            "dob": "1975-03-03",
            "sex": "M",
            "phone": unique_phone,
            "patient_type": "PRIVATE",
            "allergies": [{"substance": "Penicillin", "reaction": "Rash", "severity": "MODERATE"}],
            "next_of_kin": [{"name": "Jane Doe", "relationship": "SPOUSE", "phone": "08011122233"}],
        }
        resp = requests.post(f"{base_url}{PATIENTS_URL}", json=payload, headers=receptionist_headers)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body.get("allergies"), "Expected nested allergies to be created at registration time"
        assert body.get("next_of_kin"), "Expected nested next_of_kin to be created at registration time"

    def test_search_patient_by_mrn_after_registration(self, base_url, receptionist_headers, minimal_private_patient):
        create_resp = requests.post(f"{base_url}{PATIENTS_URL}", json=minimal_private_patient, headers=receptionist_headers)
        assert create_resp.status_code == 201, create_resp.text
        mrn = create_resp.json()["mrn"]

        search_resp = requests.get(f"{base_url}{PATIENTS_URL}", params={"search": mrn}, headers=receptionist_headers)
        assert search_resp.status_code == 200
        results = search_resp.json().get("results", search_resp.json())
        assert any(p.get("mrn") == mrn for p in results), "Registered patient not findable by its own MRN"


@pytest.mark.regression
@pytest.mark.negative
class TestPatientRegistrationNegative:

    @pytest.mark.parametrize("missing_field", ["first_name", "last_name", "dob", "sex", "phone"])
    def test_missing_required_field_returns_400(self, base_url, receptionist_headers, minimal_private_patient, missing_field):
        """
        FIXED from first run: errors are nested under 'field_errors', not
        at the top level of the response — same envelope shape as
        Authentication's error responses. Should have reused that pattern
        from the start instead of assuming a flat structure.
        """
        payload = dict(minimal_private_patient)
        del payload[missing_field]
        resp = requests.post(f"{base_url}{PATIENTS_URL}", json=payload, headers=receptionist_headers)
        assert resp.status_code == 400, resp.text
        assert missing_field in resp.json().get("field_errors", {}), (
            f"Expected a field-level error for '{missing_field}'"
        )

    def test_invalid_sex_value_returns_400(self, base_url, receptionist_headers, minimal_private_patient):
        payload = dict(minimal_private_patient)
        payload["sex"] = "X"
        resp = requests.post(f"{base_url}{PATIENTS_URL}", json=payload, headers=receptionist_headers)
        assert resp.status_code == 400, resp.text

    @pytest.mark.parametrize("field", ["first_name", "address"])
    def test_sql_injection_payload_does_not_break_the_request(self, base_url, receptionist_headers, minimal_private_patient, field):
        """
        WEAK CHECK BY DESIGN — name reflects exactly what this proves and
        no more. A 200/201/400 status code only confirms the payload didn't
        crash the request; it does NOT confirm the backend uses
        parameterized queries, and there is no database inspection here.
        A payload that succeeded silently while being stored unchanged would
        still pass this check. Real SQL-injection verification needs either
        a code-level review of the query layer, or dedicated security
        tooling — not something a black-box API test can fully prove.
        """
        payload = dict(minimal_private_patient)
        payload[field] = "'; DROP TABLE patients; --"
        resp = requests.post(f"{base_url}{PATIENTS_URL}", json=payload, headers=receptionist_headers)
        assert resp.status_code in (200, 201, 400), resp.text

    @pytest.mark.critical
    @pytest.mark.parametrize("field", ["first_name", "address"])
    def test_xss_payload_is_sanitized(self, base_url, receptionist_headers, minimal_private_patient, field):
        payload = dict(minimal_private_patient)
        payload[field] = "<script>alert(1)</script>"
        resp = requests.post(f"{base_url}{PATIENTS_URL}", json=payload, headers=receptionist_headers)
        assert resp.status_code in (200, 201, 400), resp.text
        if resp.status_code in (200, 201):
            stored_value = str(resp.json().get(field, ""))
            assert "<script>" not in stored_value, "Raw <script> tag stored/echoed unsanitized — log as a bug"

    @pytest.mark.skip(
        reason="Business rule not confirmed — does registering an HMO patient against an "
               "inactive hmo_provider succeed or get blocked? Un-skip once confirmed."
    )
    def test_register_hmo_patient_with_inactive_provider(self, base_url, receptionist_headers, unique_phone):
        pass