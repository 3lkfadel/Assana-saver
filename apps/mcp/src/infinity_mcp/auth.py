"""Bearer authentication: the token is an Infinity Planning token, checked against the API."""

import hashlib
import time

import httpx
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.dependencies import get_access_token

from .api import InfinityAPI, InfinityAPIError
from .config import Settings

# A verified token is trusted this long before being checked again
CACHE_SECONDS = 60


class InfinityTokenVerifier(TokenVerifier):
    """Accepts the tokens the Infinity Planning API accepts; the API then applies the person's rights."""

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        super().__init__(base_url=settings.public_url)
        self.settings = settings
        self._transport = transport
        self._cache: dict[str, tuple[float, AccessToken]] = {}

    async def verify_token(self, token: str) -> AccessToken | None:
        key = hashlib.sha256(token.encode()).hexdigest()
        cached = self._cache.get(key)
        if cached and cached[0] > time.monotonic():
            return cached[1]
        try:
            async with InfinityAPI(self.settings, token, self._transport) as api:
                user = await api.me()
        except InfinityAPIError:
            self._cache.pop(key, None)
            return None
        access_token = AccessToken(token=token, client_id=str(user["id"]), scopes=[], claims={"user": user})
        self._cache[key] = (time.monotonic() + CACHE_SECONDS, access_token)
        return access_token


def current_token(settings: Settings) -> str:
    """The caller's token over HTTP, or the configured one for a single-user (stdio) server."""
    access_token = get_access_token()
    if access_token is not None:
        return access_token.token
    if settings.api_token:
        return settings.api_token
    raise InfinityAPIError(
        "No Infinity Planning token: send 'Authorization: Bearer <token>' or set INFINITY_API_TOKEN."
    )
