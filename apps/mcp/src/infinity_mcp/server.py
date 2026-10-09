"""The Infinity Planning MCP server."""

from fastmcp import FastMCP

from .auth import InfinityTokenVerifier
from .deps import Deps
from .tools.read import register_read_tools

INSTRUCTIONS = """\
Infinity Planning is the organisation's work management tool, modelled on Asana.

- A project holds tasks, grouped in sections (shown as columns on the board).
- A task is identified by its project identifier and number, e.g. IAT-12; always use these identifiers
  and give the task's link to the user.
- A task is either open or completed. It has at most one assignee, a start date, a due date,
  a priority, labels and custom fields defined per project.
- Everything is done with the connected person's own permissions: a refusal means they lack access.
- Call whoami for today's date before working with relative dates, and get_project before creating
  or changing tasks, to use the exact names of sections, labels, people and custom field options.
"""


def create_server(deps: Deps, *, authenticate: bool = True) -> FastMCP:
    """``authenticate`` is off for stdio and in-memory use, where the token comes from the settings."""
    auth = InfinityTokenVerifier(deps.settings, deps.transport) if authenticate else None
    mcp = FastMCP(name="Infinity Planning", instructions=INSTRUCTIONS, auth=auth)
    register_read_tools(mcp, deps)
    return mcp
