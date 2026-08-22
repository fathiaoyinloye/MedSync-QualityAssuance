import pytest


@pytest.mark.smoke
def test_base_url_is_configured(base_url):
    assert base_url is not None
    assert base_url.startswith("http")
