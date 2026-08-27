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
_MIN_SECONDS_BETWEEN_LOGIN_CALLS = 13 


def throttle_login_call():
   
    elapsed = time.time() - _last_login_call_at["ts"]
    if elapsed < _MIN_SECONDS_BETWEEN_LOGIN_CALLS:
        time.sleep(_MIN_SECONDS_BETWEEN_LOGIN_CALLS - elapsed)
    _last_login_call_at["ts"] = time.time()


@pytest.fixture
def login_throttle():
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