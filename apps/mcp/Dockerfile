# Infinity Planning MCP server (HTTP transport), built with uv from the locked dependencies.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never

# Dependencies first: they change less often than the code.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH" \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8211 \
    MCP_PATH=/mcp

RUN useradd --system --uid 10001 mcp
USER mcp

EXPOSE 8211

CMD ["infinity-planning-mcp"]
