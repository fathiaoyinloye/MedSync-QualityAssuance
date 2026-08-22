import os
import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("MEDSYNC_BASE_URL", "http://localhost:8000")
ADMIN_EMAIL = os.getenv("MEDSYNC_ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("MEDSYNC_ADMIN_PASSWORD")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def admin_token(base_url):
    response = requests.post(
        f"{base_url}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    response.raise_for_status()
    return response.json()["token"]


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
