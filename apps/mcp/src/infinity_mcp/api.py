"""Client of the Infinity Planning public API (/api/v1), authenticated with the caller's token."""

from typing import Any, Self

import httpx
from fastmcp.exceptions import ToolError

from .config import Settings

TIMEOUT = httpx.Timeout(20.0)
# Pages read at most when a tool gathers every result of a query
MAX_PAGES = 10


class InfinityAPIError(ToolError):
    """An API error, worded for the person talking to Claude."""


def _error_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:300]
    if isinstance(body, dict):
        if isinstance(body.get("error"), str):
            return body["error"]
        if isinstance(body.get("errors"), list):
            return "; ".join(f"item {error.get('index')}: {error.get('errors')}" for error in body["errors"])
        return "; ".join(f"{key}: {value}" for key, value in body.items())
    return str(body)[:300]


def _raise_for_status(response: httpx.Response) -> None:
    if response.is_success:
        return
    status = response.status_code
    if status == 401:
        message = (
            "The Infinity Planning token is invalid or expired. "
            "Generate a new one in Infinity Planning: Profile settings > Connect Claude."
        )
    elif status == 403:
        message = "You do not have access to this in Infinity Planning."
    elif status == 404:
        message = f"Not found in Infinity Planning: {_error_detail(response)}"
    elif status == 429:
        message = "Infinity Planning's rate limit is reached; try again in a minute."
    elif status >= 500:
        message = "Infinity Planning had an internal error; try again later."
    else:
        message = f"Infinity Planning refused the request: {_error_detail(response)}"
    raise InfinityAPIError(message)


class InfinityAPI:
    """One instance per tool call; ``transport`` lets the tests replace the network."""

    def __init__(self, settings: Settings, token: str, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=f"{settings.api_url}/api/v1",
            headers={"X-Api-Key": token, "Accept": "application/json"},
            timeout=TIMEOUT,
            transport=transport,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self._client.aclose()

    def workspace_path(self, path: str) -> str:
        return f"/workspaces/{self.settings.workspace_slug}/{path.lstrip('/')}"

    async def request(self, method: str, path: str, *, params: dict | None = None, json: Any = None) -> Any:
        """Call ``path`` (relative to /api/v1) and return the decoded body."""
        clean_params = {key: value for key, value in (params or {}).items() if value is not None}
        try:
            response = await self._client.request(method, path, params=clean_params, json=json)
        except httpx.HTTPError as error:
            raise InfinityAPIError(f"Infinity Planning cannot be reached ({error.__class__.__name__}).") from error
        _raise_for_status(response)
        return response.json() if response.content else None

    async def get(self, path: str, **params: Any) -> Any:
        return await self.request("GET", self.workspace_path(path), params=params)

    async def page(self, path: str, *, cursor: str | None = None, per_page: int = 100, **params: Any) -> dict:
        """One page of a paginated listing: ``results``, ``next_cursor`` and ``has_more``."""
        body = await self.get(path, cursor=cursor, per_page=per_page, **params)
        if isinstance(body, list):
            return {"results": body, "next_cursor": None, "has_more": False, "total": len(body)}
        has_more = bool(body.get("next_page_results"))
        return {
            "results": body.get("results", []),
            "next_cursor": body.get("next_cursor") if has_more else None,
            "has_more": has_more,
            "total": body.get("total_count"),
        }

    async def all_pages(self, path: str, **params: Any) -> tuple[list, bool]:
        """Every result, up to MAX_PAGES pages; the flag tells whether some were left out."""
        results, cursor = [], None
        for _ in range(MAX_PAGES):
            page = await self.page(path, cursor=cursor, **params)
            results.extend(page["results"])
            if not page["has_more"]:
                return results, False
            cursor = page["next_cursor"]
        return results, True

    async def me(self) -> dict:
        return await self.request("GET", "/users/me/")
