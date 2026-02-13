"""Pytest global setup for deterministic test runs."""

import os
import sys
from pathlib import Path

os.environ.setdefault("PROJECT_STORE_BACKEND", "inmemory")
os.environ.setdefault("APP_ENV", "test")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from app.services.project_store import reset_project_store_for_tests


@pytest.fixture(autouse=True)
def reset_project_store_fixture():
    reset_project_store_for_tests()
    yield
    reset_project_store_for_tests()
