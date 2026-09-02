# Location: 07_Automation/API/conftest.py

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
    """Paces real login calls so our own suite doesn't trigger the API's rate limit."""
    elapsed = time.time() - _last_login_call_at["ts"]
    if elapsed < _MIN_SECONDS_BETWEEN_LOGIN_CALLS:
        time.sleep(_MIN_SECONDS_BETWEEN_LOGIN_CALLS - elapsed)
    _last_login_call_at["ts"] = time.time()


@pytest.fixture(scope="session")
def login_throttle():
    """
    Session-scoped: this just hands back a reference to the same stateless
    module-level function every time — there's no per-test state living
    inside the fixture itself (the actual rate-limit clock is the separate
    _last_login_call_at dict, which persists for the whole process
    regardless of fixture scope). Elevating this to session scope is what
    allows role_headers below to also be session-scoped.
    """
    return throttle_login_call

@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def admin_credentials():
    return {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}


@pytest.fixture(scope="session")
def admin_token(base_url):
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


# ---------------------------------------------------------------------------
# Role-based login system. ONE consistent naming scheme: every credential,
# for every role including Admin, uses the MEDSYNC_<ROLE>_EMAIL /
# MEDSYNC_<ROLE>_PASSWORD pattern. ROLE_ENV_MAP lists every role this
# project might need — a role NOT in this dict raises a clear KeyError
# naming the typo, instead of silently doing the wrong thing.
# ---------------------------------------------------------------------------

ROLE_ENV_MAP = {
    "ADMIN": ("MEDSYNC_ADMIN_EMAIL", "MEDSYNC_ADMIN_PASSWORD"),
    "FACILITY_ADMIN": ("MEDSYNC_FACILITY_ADMIN_EMAIL", "MEDSYNC_FACILITY_ADMIN_PASSWORD"),
    "RECEPTIONIST": ("MEDSYNC_RECEPTIONIST_EMAIL", "MEDSYNC_RECEPTIONIST_PASSWORD"),
    "DOCTOR": ("MEDSYNC_DOCTOR_EMAIL", "MEDSYNC_DOCTOR_PASSWORD"),
    "NURSE": ("MEDSYNC_NURSE_EMAIL", "MEDSYNC_NURSE_PASSWORD"),
    "BILLER": ("MEDSYNC_BILLER_EMAIL", "MEDSYNC_BILLER_PASSWORD"),
    "HMO_DESK": ("MEDSYNC_HMO_DESK_EMAIL", "MEDSYNC_HMO_DESK_PASSWORD"),
    "LAB_TECH": ("MEDSYNC_LAB_TECH_EMAIL", "MEDSYNC_LAB_TECH_PASSWORD"),
    "PHARMACIST": ("MEDSYNC_PHARMACIST_EMAIL", "MEDSYNC_PHARMACIST_PASSWORD"),
    "STORE_KEEPER": ("MEDSYNC_STORE_KEEPER_EMAIL", "MEDSYNC_STORE_KEEPER_PASSWORD"),
    "VIEWER": ("MEDSYNC_VIEWER_EMAIL", "MEDSYNC_VIEWER_PASSWORD"),
}


@pytest.fixture(scope="session")
def role_token_cache():
    """
    Session-scoped dict: role name -> ready-to-use headers. Each role logs
    in at most ONCE per test run, no matter how many tests ask for it —
    critical once a run needs several different role logins, since the real
    API allows only 5 total logins per minute.
    """
    return {}


@pytest.fixture(scope="session")
def role_headers(role_token_cache, base_url, login_throttle):
    """
    Fixture FACTORY — returns a function, not a fixed value, so a test can
    choose which role to log in as at call time:
        headers = role_headers("RECEPTIONIST")

    Now session-scoped (was function-scoped). This fixes a real scope
    conflict: pytest doesn't allow a broader-scoped fixture (like the
    module-scoped registered_patient in tests/patients/conftest.py) to
    depend on a narrower-scoped one. Since role_token_cache already does
    the real caching work, there's no downside to role_headers itself
    being session-scoped too — it's just handing back a small factory
    function either way.
    """
    def _get(role: str):
        role = role.upper()
        if role in role_token_cache:
            return role_token_cache[role]

        if role not in ROLE_ENV_MAP:
            raise KeyError(
                f"Unknown role '{role}'. Valid roles: {sorted(ROLE_ENV_MAP)}"
            )
        email_var, password_var = ROLE_ENV_MAP[role]
        email = os.environ.get(email_var)
        password = os.environ.get(password_var)
        if not email or not password:
            raise RuntimeError(
                f"Missing credentials for role '{role}'. Add {email_var} and "
                f"{password_var} to your .env file."
            )

        login_throttle()
        response = requests.post(
            f"{base_url}/api/v1/auth/token/",
            json={"email": email, "password": password},
        )
        response.raise_for_status()
        headers = {"Authorization": f"Bearer {response.json()['access']}"}
        role_token_cache[role] = headers
        return headers

    return _get