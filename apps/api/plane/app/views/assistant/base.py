# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import json
import os
from typing import Any, Dict, List, Optional, Tuple

# Django imports
from django.http import StreamingHttpResponse

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.db.models import Project
from plane.license.utils.instance_value import get_configuration_value

from ..base import BaseAPIView
from .agent import DEFAULT_MODEL, run_assistant
from .tools import AssistantScope, ToolInputError, build_scope, resolve_work_item

MAX_HISTORY_MESSAGES = 20
MAX_MESSAGE_CHARS = 8000


def get_assistant_config() -> Tuple[Optional[str], str]:
    api_key, model = get_configuration_value(
        [
            {"key": "ANTHROPIC_API_KEY", "default": os.environ.get("ANTHROPIC_API_KEY", "")},
            {"key": "ANTHROPIC_MODEL", "default": os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)},
        ]
    )
    return (api_key or None), (model or DEFAULT_MODEL)


def _clean_history(raw_messages: Any) -> Optional[List[Dict[str, str]]]:
    """Validate the text-only conversation sent by the client; the last message must be the user's question."""
    if not isinstance(raw_messages, list) or not raw_messages:
        return None
    messages = []
    for message in raw_messages[-MAX_HISTORY_MESSAGES:]:
        if not isinstance(message, dict):
            return None
        role, content = message.get("role"), message.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str) or not content.strip():
            return None
        messages.append({"role": role, "content": content.strip()[:MAX_MESSAGE_CHARS]})
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    if not messages or messages[-1]["role"] != "user":
        return None
    return messages


def _context_note(scope: AssistantScope, context: Any) -> Optional[str]:
    """Describe what the user is looking at (a work item or a project), if it is in scope."""
    if not isinstance(context, dict):
        return None
    try:
        if isinstance(context.get("work_item_id"), str):
            issue = resolve_work_item(scope, context["work_item_id"])
            reference = f"{issue.project.identifier}-{issue.sequence_id}"
            return f"[Context: the user is viewing work item {reference} · {issue.name}]"
        if isinstance(context.get("project_id"), str) and context["project_id"] in scope.project_ids:
            project = Project.objects.filter(id=context["project_id"]).first()
            if project:
                return f"[Context: the user is viewing project {project.identifier} · {project.name}]"
    except ToolInputError:
        return None
    return None


def _sse(event: Dict[str, Any]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


class AssistantStatusEndpoint(BaseAPIView):
    """Whether the assistant is configured and whether the current user may use it in this workspace."""

    def get(self, request, slug):
        api_key, _ = get_assistant_config()
        scope = build_scope(request.user, slug)
        return Response(
            {"is_configured": bool(api_key), "is_allowed": not scope.is_empty},
            status=status.HTTP_200_OK,
        )


class AssistantChatEndpoint(BaseAPIView):
    """Stream an answer (server-sent events) to a question about the user's projects."""

    def post(self, request, slug):
        scope = build_scope(request.user, slug)
        if scope.is_empty:
            return Response(
                {"error": "The assistant is available to workspace admins and project admins only."},
                status=status.HTTP_403_FORBIDDEN,
            )

        api_key, model = get_assistant_config()
        if not api_key:
            return Response(
                {"error": "The assistant is not configured. An instance admin must add an Anthropic API key."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        messages = _clean_history(request.data.get("messages"))
        if messages is None:
            return Response(
                {"error": "Provide 'messages': a list of {role, content} ending with the user's question."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        note = _context_note(scope, request.data.get("context"))
        if note:
            messages[-1] = {"role": "user", "content": f"{note}\n\n{messages[-1]['content']}"}

        events = run_assistant(api_key=api_key, model=model, scope=scope, messages=messages)
        response = StreamingHttpResponse((_sse(event) for event in events), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
