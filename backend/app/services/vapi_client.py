"""Thin wrapper around the Vapi REST API (https://api.vapi.ai).

Keeps auth, timeouts and error handling in one place so scripts and
controllers never build raw requests or touch the API key directly.
"""

from typing import Any

import httpx

from app.core.config import Settings, get_settings


class VapiError(Exception):
    """A non-2xx response from the Vapi API."""

    def __init__(self, status_code: int, method: str, path: str, detail: str):
        self.status_code = status_code
        super().__init__(f"Vapi {method} {path} failed ({status_code}): {detail}")


class VapiConfigError(Exception):
    """Vapi is not configured locally (e.g. VAPI_API_KEY missing)."""


class VapiClient:
    def __init__(self, settings: Settings | None = None, timeout: float = 30.0):
        settings = settings or get_settings()
        if settings.vapi_api_key is None or not settings.vapi_api_key.get_secret_value():
            raise VapiConfigError(
                "VAPI_API_KEY is not set. Add it to backend/.env (see .env.example)."
            )
        self._http = httpx.Client(
            base_url=settings.vapi_base_url,
            headers={"Authorization": f"Bearer {settings.vapi_api_key.get_secret_value()}"},
            timeout=timeout,
        )

    def __enter__(self) -> "VapiClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._http.request(method, path, **kwargs)
        if response.is_error:
            # Truncate so a large error body never floods the console.
            raise VapiError(response.status_code, method, path, response.text[:500])
        return response.json() if response.content else None

    def get(self, path: str, **params: Any) -> Any:
        return self.request("GET", path, params=params or None)

    def post(self, path: str, body: dict[str, Any]) -> Any:
        return self.request("POST", path, json=body)

    def patch(self, path: str, body: dict[str, Any]) -> Any:
        return self.request("PATCH", path, json=body)

    def delete(self, path: str) -> Any:
        return self.request("DELETE", path)

    def list(self, resource: str, limit: int = 100, **params: Any) -> list[dict[str, Any]]:
        """List resources such as "assistant", "tool" or "structured-output".

        Most endpoints return a plain array; some (structured-output) return
        {"results": [...], "metadata": {...}}.
        """
        data = self.get(f"/{resource}", limit=limit, **params)
        return data["results"] if isinstance(data, dict) else data
