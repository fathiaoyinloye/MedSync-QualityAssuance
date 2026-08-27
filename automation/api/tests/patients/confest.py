import random
import pytest


@pytest.fixture
def unique_phone():
    return "080" + "".join(random.choices("0123456789", k=8))