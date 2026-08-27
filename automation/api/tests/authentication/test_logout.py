import pytest
import requests


@pytest.mark.regression
@pytest.mark.negative
def test_logout_rejects_unauthenticated_request(base_url):
    response = requests.post(f"{base_url}/api/v1/auth/logout/", json={"refresh": "fake"})
    assert response.status_code == 401


@pytest.mark.critical
def test_logout_invalidates_the_session(base_url, admin_credentials, login_throttle):
   
    login_throttle()
    session = requests.Session()

    login_response = session.post(f"{base_url}/api/v1/auth/token/", json=admin_credentials)
    assert login_response.status_code == 200

    refresh_token = session.cookies.get("refresh_token")
    assert refresh_token is not None, "Expected a refresh_token cookie after login"

    logout_response = session.post(
        f"{base_url}/api/v1/auth/logout/",
        json={"refresh": refresh_token},
    )
    assert logout_response.status_code == 204
    refresh_attempt = session.post(f"{base_url}/api/v1/auth/token/refresh/")
    assert refresh_attempt.status_code == 401, (
        "Session should be unusable after logout, but refresh still succeeded"
    )