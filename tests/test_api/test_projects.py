"""Tests for the projects API endpoints."""

import os
import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

os.environ["PROJECT_STORE_BACKEND"] = "inmemory"

from app.main import app

client = TestClient(app)


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
    )
    assert response.status_code == 200
    data = response.json()
    assert "project_id" in data
    assert data["status"] == "started"


def test_create_project_validation():
    """Test that short descriptions are rejected."""
    response = client.post(
        "/api/v1/projects",
        json={
            "title": "Test",
            "product_description": "short",
        },
    )
    assert response.status_code == 422  # Validation error


def test_get_nonexistent_project():
    """Test 404 for nonexistent project."""
    response = client.get("/api/v1/projects/nonexistent-id/status")
    assert response.status_code == 404


def test_list_projects():
    """Test listing projects."""
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
