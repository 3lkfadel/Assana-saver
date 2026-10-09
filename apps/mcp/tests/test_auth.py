"""Bearer tokens are checked against the API, and cached for a short while."""

import respx
from conftest import API, ME, SETTINGS

from infinity_mcp.auth import InfinityTokenVerifier


async def test_valid_tokens_are_accepted_and_cached():
    verifier = InfinityTokenVerifier(SETTINGS)
    with respx.mock() as router:
        route = router.get(f"{API}/users/me/").respond(json=ME)

        first = await verifier.verify_token("plane_api_ok")
        second = await verifier.verify_token("plane_api_ok")

    assert first is second
    assert first.client_id == "u-me"
    assert first.token == "plane_api_ok"
    assert route.call_count == 1
    assert route.calls.last.request.headers["X-Api-Key"] == "plane_api_ok"


async def test_rejected_tokens_are_refused():
    verifier = InfinityTokenVerifier(SETTINGS)
    with respx.mock() as router:
        router.get(f"{API}/users/me/").respond(status_code=401, json={"detail": "Given API token is not valid"})

        assert await verifier.verify_token("plane_api_expired") is None
