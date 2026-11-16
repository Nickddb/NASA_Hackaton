import os
import tempfile

import pytest

# Runtime ledger/cases must never touch backend/data during tests: set before the app is imported.
os.environ.setdefault("ASTRACARE_STATE_DIR", tempfile.mkdtemp(prefix="astracare-test-"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)
