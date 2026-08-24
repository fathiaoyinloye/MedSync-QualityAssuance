import os
import time
import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("MEDSYNC_BASE_URL", "http://localhost:8000")
ADMIN_EMAIL = os.getenv("MEDSYNC_ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("MEDSYNC_ADMIN_PASSWORD")

_last_login_call_at = {"ts": 0}
_MIN_SECONDS_BETWEEN_LOGIN_CALLS = 13  # keeps us under the real 5-requests/min limit


def throttle_login_call():
    """
    The real /auth/token/ endpoint enforces 5 attempts/min (confirmed in
    Phase 3's API mapping, and the hard way in our first test run — a 429).
    Any test that hits the login endpoint directly should call this first,
    so our OWN suite doesn't accidentally rate-limit itself. It only sleeps
    as long as actually needed, not a fixed pause every time.
    """
    elapsed = time.time() - _last_login_call_at["ts"]
    if elapsed < _MIN_SECONDS_BETWEEN_LOGIN_CALLS:
        time.sleep(_MIN_SECONDS_BETWEEN_LOGIN_CALLS - elapsed)
    _last_login_call_at["ts"] = time.time()


@pytest.fixture
def login_throttle():
    """
    Fixture wrapper around throttle_login_call() so test files can request
    it by name (like every other fixture) instead of importing a plain
    function across files, which gets messy with pytest's file layout.
    Call it like a function inside the test: login_throttle().
    """
    return throttle_login_call


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the MedSync API, loaded from .env — never hardcoded in tests."""
    return BASE_URL


@pytest.fixture(scope="session")
def admin_credentials():
    """
    Raw email/password pulled from .env — used by tests that need to
    exercise the login call ITSELF (positive/negative login tests), as
    opposed to admin_token below, which assumes login already works and
    just wants a ready-to-use token to test something else.
    """
    return {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}


@pytest.fixture(scope="session")
def admin_token(base_url):
    """
    Logs in once per test session as Facility Admin and returns the auth token.
    Session scope = we don't re-login for every single test, only once per run.
    """
    throttle_login_call()
    response = requests.post(
        f"{base_url}/api/v1/auth/token/",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    response.raise_for_status()
    return response.json()["access"]


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}