# Location: 07_Automation/API/tests/patients/test_search.py
"""
Patient Search tests — maps to manual TC-SEARCH-001 through TC-SEARCH-020.
Read-only throughout — no side effects, unlike Registration.

NOT COVERED HERE: TC-SEARCH-012 (tenant isolation, Critical priority) —
needs a second tenant's credentials to verify a patient from one hospital
isn't visible to another. Blocked until a second tenant account exists.
"""
import pytest
import requests

PATIENTS_URL = "/api/v1/patients/"


@pytest.mark.smoke
@pytest.mark.critical
def test_search_by_full_name_returns_the_patient(base_url, receptionist_headers, registered_patient):
    query = f"{registered_patient['first_name']} {registered_patient['last_name']}"
    resp = requests.get(f"{base_url}{PATIENTS_URL}", params={"search": query}, headers=receptionist_headers)
    assert resp.status_code == 200
    results = resp.json().get("results", resp.json())
    assert any(p.get("id") == registered_patient["id"] for p in results)


@pytest.mark.regression
def test_search_is_case_insensitive(base_url, receptionist_headers, registered_patient):
    """Same name, deliberately wrong case — should still find the same patient."""
    query = registered_patient["first_name"].upper()
    resp = requests.get(f"{base_url}{PATIENTS_URL}", params={"search": query}, headers=receptionist_headers)
    assert resp.status_code == 200
    results = resp.json().get("results", resp.json())
    assert any(p.get("id") == registered_patient["id"] for p in results), (
        "Search should be case-insensitive per TC-SEARCH-005"
    )


@pytest.mark.regression
def test_search_by_partial_name_returns_the_patient(base_url, receptionist_headers, registered_patient):
    """Only the first half of the unique first_name — a substring match, not the full name."""
    partial_query = registered_patient["first_name"][:10]
    resp = requests.get(f"{base_url}{PATIENTS_URL}", params={"search": partial_query}, headers=receptionist_headers)
    assert resp.status_code == 200
    results = resp.json().get("results", resp.json())
    assert any(p.get("id") == registered_patient["id"] for p in results)


@pytest.mark.regression
@pytest.mark.negative
def test_search_nonexistent_patient_returns_no_results(base_url, receptionist_headers):
    resp = requests.get(
        f"{base_url}{PATIENTS_URL}",
        params={"search": "ZzNoSuchPatientNameZz999999"},
        headers=receptionist_headers,
    )
    assert resp.status_code == 200
    results = resp.json().get("results", resp.json())
    assert len(results) == 0


@pytest.mark.regression
def test_search_by_mrn_returns_exact_patient(base_url, receptionist_headers, registered_patient):
    resp = requests.get(
        f"{base_url}{PATIENTS_URL}",
        params={"search": registered_patient["mrn"]},
        headers=receptionist_headers,
    )
    assert resp.status_code == 200
    results = resp.json().get("results", resp.json())
    assert any(p.get("mrn") == registered_patient["mrn"] for p in results)


@pytest.mark.regression
@pytest.mark.negative
def test_empty_search_does_not_error(base_url, receptionist_headers):
    """
    Manual TC-SEARCH-007 says "Validation or no action" — genuinely
    ambiguous, so this only asserts it doesn't crash (no 500), not a
    specific exact behavior. Tighten this once the real behavior is
    confirmed either way.
    """
    resp = requests.get(f"{base_url}{PATIENTS_URL}", params={"search": ""}, headers=receptionist_headers)
    assert resp.status_code in (200, 400)


@pytest.mark.regression
@pytest.mark.negative
def test_search_with_malicious_payload_does_not_crash(base_url, receptionist_headers):
    """
    Weak check by design, same caveat as the registration SQL-injection
    test: only proves the server doesn't error out (no 500) on a hostile
    search term — does not prove the query layer is safe against injection.
    """
    resp = requests.get(
        f"{base_url}{PATIENTS_URL}",
        params={"search": "'; DROP TABLE patients; --"},
        headers=receptionist_headers,
    )
    assert resp.status_code in (200, 400), "Malicious search term should not cause a server error"


@pytest.mark.skip(
    reason="Tenant isolation (TC-SEARCH-012, Critical) needs a second tenant's "
           "credentials to verify — not yet available."
)
def test_patient_from_another_tenant_is_not_visible():
    pass# Location: 07_Automation/API/tests/patients/test_search.py
"""
Patient Search tests — maps to manual TC-SEARCH-001 through TC-SEARCH-020.
Read-only throughout — no side effects, unlike Registration.

NOT COVERED HERE: TC-SEARCH-012 (tenant isolation, Critical priority) —
needs a second tenant's credentials to verify a patient from one hospital
isn't visible to another. Blocked until a second tenant account exists.
"""
import pytest
import requests

PATIENTS_URL = "/api/v1/patients/"


@pytest.mark.smoke
@pytest.mark.critical
def test_search_by_full_name_returns_the_patient(base_url, receptionist_headers, registered_patient):
    query = f"{registered_patient['first_name']} {registered_patient['last_name']}"
    resp = requests.get(f"{base_url}{PATIENTS_URL}", params={"search": query}, headers=receptionist_headers)
    assert resp.status_code == 200
    results = resp.json().get("results", resp.json())
    assert any(p.get("id") == registered_patient["id"] for p in results)


@pytest.mark.regression
def test_search_is_case_insensitive(base_url, receptionist_headers, registered_patient):
    """Same name, deliberately wrong case — should still find the same patient."""
    query = registered_patient["first_name"].upper()
    resp = requests.get(f"{base_url}{PATIENTS_URL}", params={"search": query}, headers=receptionist_headers)
    assert resp.status_code == 200
    results = resp.json().get("results", resp.json())
    assert any(p.get("id") == registered_patient["id"] for p in results), (
        "Search should be case-insensitive per TC-SEARCH-005"
    )


@pytest.mark.regression
def test_search_by_partial_name_returns_the_patient(base_url, receptionist_headers, registered_patient):
    """Only the first half of the unique first_name — a substring match, not the full name."""
    partial_query = registered_patient["first_name"][:10]
    resp = requests.get(f"{base_url}{PATIENTS_URL}", params={"search": partial_query}, headers=receptionist_headers)
    assert resp.status_code == 200
    results = resp.json().get("results", resp.json())
    assert any(p.get("id") == registered_patient["id"] for p in results)


@pytest.mark.regression
@pytest.mark.negative
def test_search_nonexistent_patient_returns_no_results(base_url, receptionist_headers):
    resp = requests.get(
        f"{base_url}{PATIENTS_URL}",
        params={"search": "ZzNoSuchPatientNameZz999999"},
        headers=receptionist_headers,
    )
    assert resp.status_code == 200
    results = resp.json().get("results", resp.json())
    assert len(results) == 0


@pytest.mark.regression
def test_search_by_mrn_returns_exact_patient(base_url, receptionist_headers, registered_patient):
    resp = requests.get(
        f"{base_url}{PATIENTS_URL}",
        params={"search": registered_patient["mrn"]},
        headers=receptionist_headers,
    )
    assert resp.status_code == 200
    results = resp.json().get("results", resp.json())
    assert any(p.get("mrn") == registered_patient["mrn"] for p in results)


@pytest.mark.regression
@pytest.mark.negative
def test_empty_search_does_not_error(base_url, receptionist_headers):
    """
    Manual TC-SEARCH-007 says "Validation or no action" — genuinely
    ambiguous, so this only asserts it doesn't crash (no 500), not a
    specific exact behavior. Tighten this once the real behavior is
    confirmed either way.
    """
    resp = requests.get(f"{base_url}{PATIENTS_URL}", params={"search": ""}, headers=receptionist_headers)
    assert resp.status_code in (200, 400)


@pytest.mark.regression
@pytest.mark.negative
def test_search_with_malicious_payload_does_not_crash(base_url, receptionist_headers):
    """
    Weak check by design, same caveat as the registration SQL-injection
    test: only proves the server doesn't error out (no 500) on a hostile
    search term — does not prove the query layer is safe against injection.
    See test_sql_special_characters_do_not_expose_database_errors below for
    the stronger, comparison-based version of this same concern.
    """
    resp = requests.get(
        f"{base_url}{PATIENTS_URL}",
        params={"search": "'; DROP TABLE patients; --"},
        headers=receptionist_headers,
    )
    assert resp.status_code in (200, 400), "Malicious search term should not cause a server error"


@pytest.mark.critical
def test_sql_special_characters_do_not_expose_database_errors(base_url, receptionist_headers, registered_patient):
    """
    STRONGER evidence than the weak check above, using a control-vs-test
    comparison: search with a normal value first (control), then with a
    bare single-quote character (the classic SQL special character). If the
    quote causes a 500 or a raw database syntax error appears in the
    response, that's much stronger evidence of a real SQL injection risk
    than "the request technically didn't crash." This still doesn't prove
    or disprove injection with certainty (that needs query-layer code
    review or dedicated tooling) — it's a meaningfully better signal than
    a bare status-code check, not a final verdict.
    """
    control_query = registered_patient["first_name"]
    control_resp = requests.get(f"{base_url}{PATIENTS_URL}", params={"search": control_query}, headers=receptionist_headers)
    assert control_resp.status_code == 200

    quote_resp = requests.get(f"{base_url}{PATIENTS_URL}", params={"search": "'"}, headers=receptionist_headers)
    assert quote_resp.status_code in (200, 400), (
        f"A bare quote character caused an unexpected {quote_resp.status_code} — "
        f"possible SQL error exposure. Response: {quote_resp.text}"
    )
    assert "syntax error" not in quote_resp.text.lower(), (
        "Raw database syntax error exposed in response — treat as a strong SQL injection signal"
    )


@pytest.mark.skip(
    reason="Tenant isolation (TC-SEARCH-012, Critical) needs a second tenant's "
           "credentials to verify — not yet available."
)
def test_patient_from_another_tenant_is_not_visible():
    pass