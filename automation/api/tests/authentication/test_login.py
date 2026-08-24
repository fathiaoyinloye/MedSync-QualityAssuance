import pytest
import requests


@pytest.mark.smoke
@pytest.mark.critical
def test_login_with_valid_credentials(base_url, admin_credentials):
 
    response = requests.post(
        f"{base_url}/api/v1/auth/token/",
        json=admin_credentials,
    )

    assert response.status_code == 200
    body = response.json()
    assert "access" in body
    assert isinstance(body["access"], str)
    assert len(body["access"]) > 0


@pytest.mark.critical
def test_refresh_token_is_never_in_response_body(base_url, admin_credentials):
    
    response = requests.post(
        f"{base_url}/api/v1/auth/token/",
        json=admin_credentials,
    )

    assert response.status_code == 200
    assert "refresh" not in response.json()


@pytest.mark.regression
@pytest.mark.negative
@pytest.mark.parametrize(
    "email, password, case_name",
    [
        ("fathiaoyinloye21@gmail.com", "wrongpassword", "invalid_password"),
        ("not-a-real-user@gmail.com", "Temitope333", "invalid_email"),
        ("", "Temitope333", "empty_email"),
        ("fathiaoyinloye21@gmail.com", "", "empty_password"),
    ],
)
def test_login_rejects_invalid_credentials(base_url, email, password, case_name):
    response = requests.post(
        f"{base_url}/api/v1/auth/token/",
        json={"email": email, "password": password},
    )

    assert response.status_code in (400, 401), (
        f"Case '{case_name}' should have been rejected, got {response.status_code}"
    )


@pytest.mark.regression
def test_authenticated_request_succeeds_with_valid_token(base_url, auth_headers):
    response = requests.get(f"{base_url}/api/v1/auth/me/", headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.regression
@pytest.mark.negative
def test_protected_endpoint_rejects_missing_token(base_url):
    """No Authorization header at all — confirms auth is actually enforced."""
    response = requests.get(f"{base_url}/api/v1/auth/me/")
    assert response.status_code == 401


@pytest.mark.regression
@pytest.mark.negative
def test_protected_endpoint_rejects_garbage_token(base_url):
    """Present but invalid token — a different failure mode than no token at all."""
    bad_headers = {"Authorization": "Bearer this.is.not.a.real.token"}
    response = requests.get(f"{base_url}/api/v1/auth/me/", headers=bad_headers)
    assert response.status_code == 401