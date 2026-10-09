# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Work items across every project of the caller, with simple filters.

The project listing of API v1 has no filters on this edition; this endpoint answers questions such as
"my open tasks due this week" or "overdue tasks of these projects" in one paginated call.
"""

# Python imports
import uuid
from datetime import date

# Django imports
from django.db.models import Exists, OuterRef, Prefetch, Q
from django.utils.dateparse import parse_datetime

# Third party imports
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

# Module imports
from plane.db.models import Issue, IssueAssignee, IssueLabel
from plane.utils.openapi import (
    CURSOR_PARAMETER,
    FORBIDDEN_RESPONSE,
    PER_PAGE_PARAMETER,
    UNAUTHORIZED_RESPONSE,
    WORKSPACE_SLUG_PARAMETER,
)
from plane.utils.order_queryset import sanitize_order_by

from .base import BaseAPIView

COMPLETED_GROUPS = ("completed", "cancelled")
ORDER_BY_ALLOWLIST = {"target_date", "start_date", "updated_at", "created_at", "sequence_id"}
PRIORITIES = {"urgent", "high", "medium", "low", "none"}


class WorkItemQueryResultSerializer(serializers.Serializer):
    """A compact work item, with what is needed to read it without further calls."""

    id = serializers.UUIDField()
    identifier = serializers.SerializerMethodField(help_text="Project identifier and sequence, e.g. IAT-12")
    name = serializers.CharField()
    project = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    completed = serializers.SerializerMethodField()
    priority = serializers.CharField()
    start_date = serializers.DateField()
    target_date = serializers.DateField()
    assignees = serializers.SerializerMethodField()
    labels = serializers.SerializerMethodField()
    parent_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    def get_identifier(self, issue) -> str:
        return f"{issue.project.identifier}-{issue.sequence_id}"

    def get_project(self, issue) -> dict:
        return {"id": str(issue.project_id), "identifier": issue.project.identifier, "name": issue.project.name}

    def get_state(self, issue) -> dict | None:
        if issue.state is None:
            return None
        return {"id": str(issue.state_id), "name": issue.state.name, "group": issue.state.group}

    def get_completed(self, issue) -> bool:
        return issue.state is not None and issue.state.group in COMPLETED_GROUPS

    def get_assignees(self, issue) -> list:
        return [
            {"id": str(link.assignee_id), "display_name": link.assignee.display_name} for link in issue.query_assignees
        ]

    def get_labels(self, issue) -> list:
        return [{"id": str(link.label_id), "name": link.label.name} for link in issue.query_labels]


def _uuid_list(raw: str) -> list[str] | None:
    """Comma-separated UUIDs; None when one is malformed."""
    values = [value.strip() for value in raw.split(",") if value.strip()]
    try:
        return [str(uuid.UUID(value)) for value in values]
    except ValueError:
        return None


def _filter_param(name: str, description: str) -> OpenApiParameter:
    return OpenApiParameter(name=name, description=description, required=False, type=OpenApiTypes.STR)


class WorkspaceWorkItemQueryAPIEndpoint(BaseAPIView):
    """Work items of the projects the caller is a member of, filtered."""

    use_read_replica = True

    def _filter(self, request, queryset):
        """Apply the query parameters; returns the queryset, or an error message."""
        params = request.query_params

        if params.get("project"):
            project_ids = _uuid_list(params["project"])
            if project_ids is None:
                return None, "project must be a comma-separated list of project ids."
            queryset = queryset.filter(project_id__in=project_ids)

        assignee = params.get("assignee")
        if assignee:
            # The default manager leaves out removed assignments
            assignments = IssueAssignee.objects.filter(issue_id=OuterRef("pk"))
            if assignee == "none":
                queryset = queryset.filter(~Exists(assignments))
            else:
                assignee_ids = [str(request.user.id)] if assignee == "me" else _uuid_list(assignee)
                if assignee_ids is None:
                    return None, "assignee must be 'me', 'none' or comma-separated user ids."
                queryset = queryset.filter(Exists(assignments.filter(assignee_id__in=assignee_ids)))

        completed = params.get("completed")
        if completed in ("true", "false"):
            done = Q(state__group__in=COMPLETED_GROUPS)
            queryset = queryset.filter(done) if completed == "true" else queryset.exclude(done)
        elif completed:
            return None, "completed must be true or false."

        for name, lookup in (("due_before", "target_date__lte"), ("due_after", "target_date__gte")):
            if params.get(name):
                try:
                    queryset = queryset.filter(**{lookup: date.fromisoformat(params[name])})
                except ValueError:
                    return None, f"{name} must be a date (YYYY-MM-DD)."

        if params.get("updated_after"):
            updated_after = parse_datetime(params["updated_after"])
            if updated_after is None:
                return None, "updated_after must be an ISO 8601 date and time."
            queryset = queryset.filter(updated_at__gte=updated_after)

        if params.get("priority"):
            priorities = {value.strip() for value in params["priority"].split(",") if value.strip()}
            if not priorities <= PRIORITIES:
                return None, f"priority must be among {', '.join(sorted(PRIORITIES))}."
            queryset = queryset.filter(priority__in=priorities)

        if params.get("state"):
            state_ids = _uuid_list(params["state"])
            if state_ids is None:
                return None, "state must be a comma-separated list of ids."
            queryset = queryset.filter(state_id__in=state_ids)

        if params.get("label"):
            label_ids = _uuid_list(params["label"])
            if label_ids is None:
                return None, "label must be a comma-separated list of ids."
            queryset = queryset.filter(
                Exists(IssueLabel.objects.filter(issue_id=OuterRef("pk"), label_id__in=label_ids))
            )

        if params.get("parent"):
            parent_ids = _uuid_list(params["parent"])
            if parent_ids is None or len(parent_ids) != 1:
                return None, "parent must be a work item id."
            queryset = queryset.filter(parent_id=parent_ids[0])

        search = params.get("search", "").strip()
        if search:
            condition = Q(name__icontains=search)
            if search.isdigit():
                condition |= Q(sequence_id=int(search))
            queryset = queryset.filter(condition)

        return queryset, None

    @extend_schema(
        tags=["Work Items"],
        operation_id="query_workspace_work_items",
        summary="Query work items across projects",
        description=(
            "Work items of every project the caller is a member of, with optional filters. "
            "Results are compact and include the project, state, assignees and labels."
        ),
        parameters=[
            WORKSPACE_SLUG_PARAMETER,
            _filter_param("project", "Comma-separated project ids"),
            _filter_param("assignee", "'me', 'none' or comma-separated user ids"),
            _filter_param("completed", "true or false"),
            _filter_param("due_before", "Due date on or before (YYYY-MM-DD)"),
            _filter_param("due_after", "Due date on or after (YYYY-MM-DD)"),
            _filter_param("updated_after", "Updated at or after (ISO 8601)"),
            _filter_param("priority", "Comma-separated: urgent, high, medium, low, none"),
            _filter_param("state", "Comma-separated state ids"),
            _filter_param("label", "Comma-separated label ids"),
            _filter_param("parent", "Subtasks of this work item id"),
            _filter_param("search", "Text in the name, or a sequence number"),
            _filter_param(
                "order_by",
                "target_date (default), start_date, updated_at, created_at or sequence_id; '-' for descending",
            ),
            CURSOR_PARAMETER,
            PER_PAGE_PARAMETER,
        ],
        responses={
            200: OpenApiResponse(description="Paginated work items", response=WorkItemQueryResultSerializer(many=True)),
            400: OpenApiResponse(description="Invalid filter"),
            401: UNAUTHORIZED_RESPONSE,
            403: FORBIDDEN_RESPONSE,
        },
    )
    def get(self, request, slug):
        queryset = (
            Issue.issue_objects.filter(
                workspace__slug=slug,
                project__project_projectmember__member=request.user,
                project__project_projectmember__is_active=True,
                project__archived_at__isnull=True,
            )
            .select_related("project", "state")
            .prefetch_related(
                Prefetch(
                    "issue_assignee",
                    queryset=IssueAssignee.objects.select_related("assignee"),
                    to_attr="query_assignees",
                ),
                Prefetch("label_issue", queryset=IssueLabel.objects.select_related("label"), to_attr="query_labels"),
            )
        )
        queryset, error = self._filter(request, queryset)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        # Empty dates come last, in both directions
        order_by = sanitize_order_by(
            request.query_params.get("order_by", "target_date"), ORDER_BY_ALLOWLIST, "target_date"
        )
        return self.paginate(
            request=request,
            queryset=queryset.distinct(),
            order_by=order_by,
            on_results=lambda issues: WorkItemQueryResultSerializer(issues, many=True).data,
            default_per_page=50,
            max_per_page=100,
        )
