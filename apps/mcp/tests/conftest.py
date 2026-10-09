"""An in-memory server talking to a simulated Infinity Planning API."""

from datetime import date

import pytest
import respx
from fastmcp import Client

from infinity_mcp.config import Settings
from infinity_mcp.deps import Deps
from infinity_mcp.server import create_server

API = "http://api.test/api/v1"
WS = f"{API}/workspaces/infinity"
TODAY = date(2026, 10, 9)

SETTINGS = Settings(api_url="http://api.test", web_url="https://plan.test", workspace_slug="infinity", api_token="tok")

ME = {"id": "u-me", "display_name": "Awa", "email": "awa@infinity-africa.com"}
PROJECT = {"id": "p-iat", "identifier": "IAT", "name": "Infinity Africa Tech", "description": "", "archived_at": None}
STATES = [
    {"id": "s-todo", "name": "À faire", "group": "unstarted", "sequence": 1, "default": True},
    {"id": "s-done", "name": "Terminé", "group": "completed", "sequence": 2},
]
MEMBERS = [
    {
        "id": "u-me",
        "membership_id": "m-me",
        "display_name": "Awa",
        "email": "awa@infinity-africa.com",
        "is_active": True,
    },
    {
        "id": "u-kofi",
        "membership_id": "m-kofi",
        "display_name": "Kofi",
        "email": "kofi@infinity-africa.com",
        "is_active": True,
    },
]
LABELS = [{"id": "l-client", "name": "Client"}]
BUDGET = {"id": "cf-budget", "name": "Budget", "field_type": "number", "options": []}
WAVE = {
    "id": "cf-wave",
    "name": "Vague",
    "field_type": "single_select",
    "options": [{"id": "o-1", "name": "Vague 1"}, {"id": "o-2", "name": "Vague 2"}],
}


def page(results, more=False):
    return {"results": results, "next_page_results": more, "next_cursor": "100:1:0", "total_count": len(results)}


def query_item(number, name, *, due=None, done=False, assignees=("Awa",), parent=None):
    return {
        "id": f"t-{number}",
        "identifier": f"IAT-{number}",
        "name": name,
        "project": {"id": "p-iat", "identifier": "IAT", "name": "Infinity Africa Tech"},
        "state": {"id": "s-done" if done else "s-todo", "name": "Terminé" if done else "À faire"},
        "completed": done,
        "priority": "none",
        "start_date": None,
        "target_date": due,
        "assignees": [{"id": f"u-{person.lower()}", "display_name": person} for person in assignees],
        "labels": [],
        "parent_id": parent,
    }


@pytest.fixture
def api():
    with respx.mock(assert_all_called=False) as router:
        router.get(f"{API}/users/me/").respond(json=ME)
        router.get(f"{WS}/projects/").respond(json=page([PROJECT]))
        router.get(f"{WS}/projects/p-iat/states/").respond(json=page(STATES))
        router.get(f"{WS}/projects/p-iat/labels/").respond(json=page(LABELS))
        router.get(f"{WS}/projects/p-iat/project-members-lite/").respond(json=page(MEMBERS))
        router.get(f"{WS}/projects/p-iat/custom-fields/").respond(
            json=[{"custom_field": BUDGET}, {"custom_field": WAVE}]
        )
        yield router


@pytest.fixture
def server():
    return create_server(Deps(SETTINGS, clock=lambda: TODAY), authenticate=False)


@pytest.fixture
async def call(server):
    async with Client(server) as client:

        async def _call(tool, **arguments):
            result = await client.call_tool(tool, arguments)
            return result.data

        yield _call


@pytest.fixture
async def call_error(server):
    async with Client(server) as client:

        async def _call(tool, **arguments):
            result = await client.call_tool(tool, arguments, raise_on_error=False)
            assert result.is_error
            return result.content[0].text

        yield _call
