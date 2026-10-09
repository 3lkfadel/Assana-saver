# Infinity Planning MCP server

Lets Claude (Claude Code, Claude Desktop) read and update Infinity Planning with the connected person's own permissions. The server only calls the public API (`/api/v1`) with the person's Claude token; see `docs/adr/0005-connecteur-mcp-pour-claude.md`.

## Tools

| Tool               | What it does                                                                            |
| ------------------ | --------------------------------------------------------------------------------------- |
| `whoami`           | Connected person, organisation, today's date                                            |
| `list_projects`    | Projects the person can access                                                          |
| `get_project`      | Sections, labels, members and custom fields of a project                                |
| `search_tasks`     | Tasks across projects by person, completion, due date, section, label, priority or text |
| `my_tasks`         | The person's open tasks: overdue, due soon, without due date                            |
| `get_task`         | One task in full: description, custom fields, subtasks, comments, history               |
| `project_overview` | Open/done counts, overdue tasks, due this week, workload by person and section          |

All tools are read-only for now; write tools come next.

## Configuration

| Variable                             | Default                       |                                                              |
| ------------------------------------ | ----------------------------- | ------------------------------------------------------------ |
| `INFINITY_API_URL`                   | required                      | API as reached by the server, e.g. `http://localhost:8010`   |
| `INFINITY_WORKSPACE_SLUG`            | required                      | The organisation's workspace                                 |
| `INFINITY_WEB_URL`                   | `INFINITY_API_URL`            | Web app, for the links given to Claude                       |
| `INFINITY_API_TOKEN`                 | —                             | Token for `stdio` (single user); HTTP clients send their own |
| `MCP_HOST` / `MCP_PORT` / `MCP_PATH` | `127.0.0.1` / `8211` / `/mcp` | HTTP listener                                                |
| `MCP_PUBLIC_URL`                     | —                             | Public URL of the server when it runs behind a proxy         |

## Run locally

```bash
cd apps/mcp
uv sync
INFINITY_API_URL=http://localhost:8010 INFINITY_WEB_URL=http://localhost:3000 \
INFINITY_WORKSPACE_SLUG=<workspace> uv run infinity-planning-mcp
```

Then generate a token in Infinity Planning (Profile settings > Connect Claude, with `VITE_MCP_URL=http://localhost:8211/mcp` in `apps/web/.env`) and add the server to Claude Code:

```bash
claude mcp add --transport http infinity-planning http://localhost:8211/mcp --header "Authorization: Bearer <token>"
```

Requests without a valid token get `401`. A token is checked against the API, then trusted for 60 seconds.

## Tests

```bash
uv run pytest      # in-memory server, API simulated with respx
uv run ruff check
```
