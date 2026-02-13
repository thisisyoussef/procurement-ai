"""Tests for the projects API endpoints."""

import os
import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.core.auth import AuthUser, create_access_token

os.environ["PROJECT_STORE_BACKEND"] = "inmemory"

from app.main import app

client = TestClient(app)


def _auth_headers(user_id: str = "00000000-0000-0000-0000-000000000001") -> dict[str, str]:
    token, _ = create_access_token(AuthUser(user_id=user_id, email="test@example.com"))
    return {"Authorization": f"Bearer {token}"}


def test_root():
    """Test root endpoint returns app info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "Tamkin"
    assert data["status"] == "running"


def test_health():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_project():
    """Test creating a new sourcing project."""
    response = client.post(
        "/api/v1/projects",
        json={
            "title": "Test Project",
            "product_description": "I need 500 custom canvas tote bags for my brand",
        },
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert "project_id" in data
    assert data["status"] == "started"


def test_create_project_requires_auth():
    response = client.post(
        "/api/v1/projects",
        json={
            "title": "Test Project",
            "product_description": "I need 500 custom canvas tote bags for my brand",
        },
    )
    assert response.status_code == 401


def test_create_project_validation():
    """Test that short descriptions are rejected."""
    response = client.post(
        "/api/v1/projects",
        json={
            "title": "Test",
            "product_description": "short",
        },
        headers=_auth_headers(),
    )
    assert response.status_code == 422  # Validation error


def test_get_nonexistent_project():
    """Test 404 for nonexistent project."""
    response = client.get("/api/v1/projects/nonexistent-id/status", headers=_auth_headers())
    assert response.status_code == 404


def test_list_projects():
    """Test listing projects."""
    response = client.get("/api/v1/projects", headers=_auth_headers())
    assert response.status_code == 200
    assert isinstance(response.json(), list)
