"""Async backend API client for driving full sourcing runs externally."""

from __future__ import annotations

from typing import Any

import httpx


class BackendClientError(RuntimeError):
    """Raised when backend API calls fail."""


class BackendClient:
    def __init__(
        self,
        *,
        base_url: str,
        access_token: str,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.timeout_seconds = timeout_seconds
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "BackendClient":
        self._client = httpx.AsyncClient(timeout=self.timeout_seconds)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        if self._client is None:
            raise BackendClientError("BackendClient is not initialized (missing async context manager)")

        url = f"{self.base_url}{path}"
        response = await self._client.request(
            method,
            url,
            headers=self._headers,
            json=json_body,
            params=params,
        )

        if response.status_code >= 400:
            snippet = response.text[:500]
            raise BackendClientError(
                f"{method} {path} failed with {response.status_code}: {snippet}"
            )

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        if not response.text:
            return None
        return response.text

    async def health_check(self) -> dict[str, Any]:
        if self._client is None:
            raise BackendClientError("BackendClient is not initialized (missing async context manager)")
        response = await self._client.get(f"{self.base_url}/health")
        if response.status_code >= 400:
            raise BackendClientError(f"GET /health failed with {response.status_code}: {response.text[:500]}")
        return response.json()

    async def create_project(
        self,
        *,
        title: str,
        product_description: str,
        auto_outreach: bool,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/api/v1/projects",
            json_body={
                "title": title,
                "product_description": product_description,
                "auto_outreach": auto_outreach,
            },
        )

    async def get_project_status(self, project_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/v1/projects/{project_id}/status")

    async def answer_clarifying_questions(
        self,
        *,
        project_id: str,
        answers: dict[str, str],
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/v1/projects/{project_id}/answer",
            json_body={"answers": answers},
        )

    async def skip_clarifying_questions(self, project_id: str) -> dict[str, Any]:
        return await self._request("POST", f"/api/v1/projects/{project_id}/skip-questions")

    async def restart_project(
        self,
        *,
        project_id: str,
        from_stage: str,
        additional_context: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/v1/projects/{project_id}/restart",
            json_body={"from_stage": from_stage, "additional_context": additional_context},
        )

    async def cancel_project(self, project_id: str) -> dict[str, Any]:
        return await self._request("POST", f"/api/v1/projects/{project_id}/cancel")

    async def get_project_logs(self, project_id: str) -> list[dict[str, Any]]:
        logs = await self._request("GET", f"/api/v1/projects/{project_id}/logs")
        if isinstance(logs, list):
            return logs
        return []

    async def get_dashboard_activity(
        self,
        *,
        limit: int = 100,
        cursor: float | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        return await self._request("GET", "/api/v1/dashboard/activity", params=params)

