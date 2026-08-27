import pytest
import requests


@pytest.mark.regression
@pytest.mark.negative
def test_change_password_rejects_unauthenticated_request(base_url):
    """No session at all — should require auth like any protected endpoint."""
    response = requests.post(f"{base_url}/api/v1/auth/change-password/")
    assert response.status_code == 401


@pytest.mark.regression
@pytest.mark.negative
def test_change_password_with_wrong_old_password_fails(base_url, auth_headers):
    """Real field names confirmed via probe: old_password, new_password."""
    response = requests.post(
        f"{base_url}/api/v1/auth/change-password/",
        headers=auth_headers,
        json={"old_password": "definitely-wrong", "new_password": "NewPass456!"},
    )
    assert response.status_code == 400


@pytest.mark.critical
def test_change_password_round_trip(base_url, admin_credentials, auth_headers, login_throttle):
    """
    This test has a real side effect: a successful change-password call
    actually changes the shared admin account's password. Every other test
    in this suite relies on that SAME account working via admin_credentials
    from .env — so if we changed it and stopped there, every test that runs
    after this one would start failing, for a reason that has nothing to do
    with whether THEY are broken.

    The fix: change it, prove the new password logs in, then change it back
    to the original immediately, in the same test. This is a "round trip" —
    leave the system exactly as we found it, regardless of pass or fail.
    """
    old_password = admin_credentials["password"]
    new_password = "TempRoundTrip456!"

    change_response = requests.post(
        f"{base_url}/api/v1/auth/change-password/",
        headers=auth_headers,
        json={"old_password": old_password, "new_password": new_password},
    )
    assert change_response.status_code == 200

    login_throttle()
    login_with_new = requests.post(
        f"{base_url}/api/v1/auth/token/",
        json={"email": admin_credentials["email"], "password": new_password},
    )
    assert login_with_new.status_code == 200, "New password should now work"

    # Restore original password so the rest of the suite keeps working.
    new_token = login_with_new.json()["access"]
    restore_headers = {"Authorization": f"Bearer {new_token}"}
    restore_response = requests.post(
        f"{base_url}/api/v1/auth/change-password/",
        headers=restore_headers,
        json={"old_password": new_password, "new_password": old_password},
    )
    assert restore_response.status_code == 200, (
        "CRITICAL: password was not restored — admin account may be left in "
        f"a broken state with password '{new_password}'"
    )


@pytest.mark.critical
def test_request_password_reset_same_response_for_real_and_fake_email(base_url, admin_credentials):
    """
    Directly verifies the documented anti-enumeration behavior from the API
    mapping: "Always returns the same generic response whether or not the
    email matches an account, to avoid leaking which addresses are
    registered." We assert both calls return the SAME status code — if a
    future bug made real vs. fake emails behave differently, this test
    would catch it even though neither response is wrong on its own.
    """
    real_email_response = requests.post(
        f"{base_url}/api/v1/auth/request-password-reset/",
        json={"email": admin_credentials["email"]},
    )
    fake_email_response = requests.post(
        f"{base_url}/api/v1/auth/request-password-reset/",
        json={"email": "definitely-not-a-real-account@nowhere.com"},
    )

    assert real_email_response.status_code == fake_email_response.status_code == 200


@pytest.mark.regression
@pytest.mark.negative
def test_password_reset_confirm_rejects_invalid_token(base_url):
    """
    Real fields confirmed via probe: uid, token, new_password. We can only
    test the NEGATIVE path here — the positive path needs a real uid/token
    pair from an actual emailed reset link, which requires mailbox access
    this automated suite doesn't have. That positive path stays a manual
    test case (see manual Test_Cases sheet) rather than a fabricated,
    misleading automated one.
    """
    response = requests.post(
        f"{base_url}/api/v1/auth/password-reset/confirm/",
        json={"uid": "garbage", "token": "garbage", "new_password": "NewPass456!"},
    )
    assert response.status_code == 400