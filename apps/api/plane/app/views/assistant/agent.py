# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Claude-powered, read-only project assistant: streaming tool-use loop."""

# Python imports
import json
from typing import Any, Dict, Iterator, List

# Third party imports
import anthropic

# Module imports
from plane.utils.exception_logger import log_exception

from .tools import TOOL_DEFINITIONS, AssistantScope, ToolInputError, run_tool

DEFAULT_MODEL = "claude-opus-5-5"
MAX_TOKENS = 16000
MAX_TOOL_ROUNDS = 8
MAX_INVALID_JSON_RETRIES = 2
FALLBACK_BETA = "server-side-fallback-2026-07-01"

SYSTEM_PROMPT = """You are the project assistant of Infinity Planning, a project management tool.
You help project managers and workspace administrators understand where their work stands.

How to work:
- Answer from the data returned by your tools. Never invent work items, dates, people or numbers.
- Look up what you need before answering: resolve vague names with search_work_items or list_projects,
  then read details with get_work_item, project_progress, deadline_report or member_workload.
- Deadline verdicts (overdue, completed late, days late, on track) are computed by the tools from the
  due date and the completion date. Report them as given; do not recompute dates yourself.
- When an item has no due date, say so instead of judging whether it is late.
- If the data does not answer the question, say what is missing.
- You are read-only. If asked to create, modify, assign or move something, explain that you can only
  consult data in this version and say what the user could do in the app.

How to answer:
- Reply in French by default. If the user writes in another language, reply in that language.
- Be concise and lead with the answer. Use short lists or a small table when comparing several items.
- Refer to work items by reference and name, e.g. "IAT-12 · Migration Exchange OBF".
- Write dates as day month year (e.g. 7 août 2026)."""


def _tools_for_request() -> List[Dict[str, Any]]:
    # Inputs stream as they are generated; the tools validate their own arguments.
    return [{**tool, "eager_input_streaming": True} for tool in TOOL_DEFINITIONS]


def _event(event_type: str, **payload: Any) -> Dict[str, Any]:
    return {"type": event_type, **payload}


def run_assistant(
    *,
    api_key: str,
    model: str,
    scope: AssistantScope,
    messages: List[Dict[str, Any]],
) -> Iterator[Dict[str, Any]]:
    """
    Run the tool-use loop and yield UI events:
    ``status`` (a tool is running), ``text`` (answer delta), ``error`` and a final ``done``.
    """
    client = anthropic.Anthropic(api_key=api_key)
    tools = _tools_for_request()
    conversation: List[Dict[str, Any]] = list(messages)
    invalid_json_retries = 0
    tool_rounds = 0

    try:
        while True:
            try:
                with client.beta.messages.stream(
                    model=model,
                    max_tokens=MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    tools=tools,
                    messages=conversation,
                    output_config={"effort": "medium"},
                    cache_control={"type": "ephemeral"},
                    betas=[FALLBACK_BETA],
                    fallbacks="default",
                ) as stream:
                    for event in stream:
                        if event.type == "text":
                            yield _event("text", text=event.text)
                    response = stream.get_final_message()
                invalid_json_retries = 0
            except ValueError:
                # Tool input JSON the SDK could not parse: re-issue the turn (bounded).
                invalid_json_retries += 1
                if invalid_json_retries > MAX_INVALID_JSON_RETRIES:
                    raise
                continue

            if response.stop_reason == "refusal":
                yield _event("error", code="refusal")
                break

            conversation.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "pause_turn":
                continue

            tool_uses = [block for block in response.content if block.type == "tool_use"]
            if not tool_uses:
                if response.stop_reason == "max_tokens":
                    yield _event("error", code="truncated")
                break
            if response.stop_reason == "max_tokens":
                # A truncated tool input parses as a partial object; never run it.
                yield _event("error", code="truncated")
                break

            tool_rounds += 1
            if tool_rounds > MAX_TOOL_ROUNDS:
                yield _event("error", code="too_many_steps")
                break

            tool_results = []
            for block in tool_uses:
                yield _event("status", tool=block.name)
                try:
                    content = run_tool(scope, block.name, block.input)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": content})
                except ToolInputError as error:
                    tool_results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": str(error), "is_error": True}
                    )
                except Exception as error:  # a data error must not end the conversation
                    log_exception(error)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({"error": "The data lookup failed."}),
                            "is_error": True,
                        }
                    )
            conversation.append({"role": "user", "content": tool_results})
    except anthropic.AuthenticationError:
        yield _event("error", code="invalid_api_key")
    except anthropic.PermissionDeniedError:
        yield _event("error", code="permission_denied")
    except anthropic.NotFoundError:
        yield _event("error", code="model_not_found")
    except anthropic.RateLimitError:
        yield _event("error", code="rate_limited")
    except anthropic.APIStatusError as error:
        log_exception(error)
        yield _event("error", code="api_error")
    except anthropic.APIConnectionError:
        yield _event("error", code="connection_error")
    except Exception as error:
        log_exception(error)
        yield _event("error", code="unexpected_error")

    yield _event("done")
