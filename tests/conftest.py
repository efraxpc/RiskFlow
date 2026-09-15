import pytest
from fastapi.testclient import TestClient

from supportflow.config import Settings
from supportflow.main import create_app


@pytest.fixture
def app():
    return create_app(Settings(_env_file=None, rate_limit=1000))


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client
