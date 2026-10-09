"""Settings, read from the environment."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # Infinity Planning API, as reached by this server (e.g. http://api:8000 inside Docker)
    api_url: str
    # Web app, for the links given to Claude
    web_url: str
    # The organisation's workspace: the server serves a single one
    workspace_slug: str
    # Token used when the client sends none (stdio, single user); HTTP clients send their own
    api_token: str | None = None
    host: str = "127.0.0.1"
    port: int = 8211
    path: str = "/mcp"
    # Public URL of this server, advertised to clients when it runs behind a proxy
    public_url: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        missing = [name for name in ("INFINITY_API_URL", "INFINITY_WORKSPACE_SLUG") if not os.environ.get(name)]
        if missing:
            raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")
        api_url = os.environ["INFINITY_API_URL"].rstrip("/")
        return cls(
            api_url=api_url,
            web_url=os.environ.get("INFINITY_WEB_URL", api_url).rstrip("/"),
            workspace_slug=os.environ["INFINITY_WORKSPACE_SLUG"],
            api_token=os.environ.get("INFINITY_API_TOKEN") or None,
            host=os.environ.get("MCP_HOST", "127.0.0.1"),
            port=int(os.environ.get("MCP_PORT", "8211")),
            path=os.environ.get("MCP_PATH", "/mcp"),
            public_url=os.environ.get("MCP_PUBLIC_URL") or None,
        )
