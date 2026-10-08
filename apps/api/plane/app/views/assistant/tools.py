# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Read-only data tools exposed to the AI assistant.

Every tool runs inside an ``AssistantScope``: the set of projects the asking user may query.
Deadline facts (late / on time / days late) are computed here, never left to the model.
"""

# Python imports
import json
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Dict, List, Optional

# Django imports
from django.db.models import Q
from django.utils import timezone

# Module imports
from plane.app.permissions import ROLE
from plane.db.models import (
    Cycle,
    CycleIssue,
    Issue,
    IssueActivity,
    IssueComment,
    Module,
    ModuleIssue,
    Project,
    ProjectMember,
    WorkspaceMember,
)

MAX_LIST_RESULTS = 50
MAX_DESCRIPTION_CHARS = 2000
MAX_ACTIVITIES = 30
MAX_COMMENTS = 20

WORK_ITEM_REF_PATTERN = re.compile(r"^\s*([A-Za-z0-9]+)-(\d+)\s*$")


class ToolInputError(ValueError):
    """Raised when the model passes invalid tool arguments; reported back to it as an error result."""


@dataclass(frozen=True)
class AssistantScope:
    workspace_slug: str
    user_id: str
    project_ids: frozenset

    @property
    def is_empty(self) -> bool:
        return not self.project_ids


def build_scope(user, workspace_slug: str) -> AssistantScope:
    """
    Projects the user may query through the assistant:
    - workspace admins: every active project they are a member of;
    - project admins: the projects they administer.
    Everyone else gets an empty scope (no access to the assistant).
    """
    is_workspace_admin = WorkspaceMember.objects.filter(
        member=user, workspace__slug=workspace_slug, role=ROLE.ADMIN.value, is_active=True
    ).exists()
    memberships = ProjectMember.objects.filter(
        member=user,
        workspace__slug=workspace_slug,
        is_active=True,
        project__archived_at__isnull=True,
    )
    if not is_workspace_admin:
        memberships = memberships.filter(role=ROLE.ADMIN.value)
    project_ids = frozenset(str(project_id) for project_id in memberships.values_list("project_id", flat=True))
    return AssistantScope(workspace_slug=workspace_slug, user_id=str(user.id), project_ids=project_ids)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _today() -> date:
    return timezone.localdate()


def deadline_status(target_date: Optional[date], state_group: str, completed_at, today: date) -> Dict[str, Any]:
    """Deterministic deadline verdict for one work item."""
    if not target_date:
        return {"status": "no_due_date"}
    if state_group == "cancelled":
        return {"status": "cancelled"}
    if state_group == "completed":
        if not completed_at:
            return {"status": "completed_date_unknown"}
        completed_on = (
            timezone.localtime(completed_at).date() if timezone.is_aware(completed_at) else completed_at.date()
        )
        days_late = (completed_on - target_date).days
        if days_late > 0:
            return {"status": "completed_late", "days_late": days_late, "completed_on": completed_on.isoformat()}
        return {"status": "completed_on_time", "completed_on": completed_on.isoformat()}
    days_late = (today - target_date).days
    if days_late > 0:
        return {"status": "overdue", "days_late": days_late}
    return {"status": "on_track", "days_remaining": -days_late}


def _optional_str(args: Dict[str, Any], key: str, max_length: int = 200) -> Optional[str]:
    value = args.get(key)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ToolInputError(f"'{key}' must be a string.")
    return value.strip()[:max_length] or None


def _optional_bool(args: Dict[str, Any], key: str, default: bool = False) -> bool:
    value = args.get(key, default)
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ToolInputError(f"'{key}' must be a boolean.")
    return value


def _optional_int(args: Dict[str, Any], key: str, default: int, minimum: int, maximum: int) -> int:
    value = args.get(key, default)
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise ToolInputError(f"'{key}' must be an integer.")
    return max(minimum, min(maximum, value))


def _scoped_projects(scope: AssistantScope):
    return Project.objects.filter(id__in=scope.project_ids, archived_at__isnull=True)


def _resolve_project(scope: AssistantScope, project_ref: Optional[str]) -> Optional[Project]:
    """Find a project in scope by identifier (e.g. ``IAT``), exact name, or partial name."""
    if not project_ref:
        return None
    projects = _scoped_projects(scope)
    project = (
        projects.filter(identifier__iexact=project_ref).first()
        or projects.filter(name__iexact=project_ref).first()
        or projects.filter(name__icontains=project_ref).first()
    )
    if not project:
        raise ToolInputError(
            f"No accessible project matches '{project_ref}'. Call list_projects to see the projects you can query."
        )
    return project


def _scoped_issues(scope: AssistantScope):
    return Issue.issue_objects.filter(project_id__in=scope.project_ids).select_related("state", "project")


def _work_item_ref(issue: Issue) -> str:
    return f"{issue.project.identifier}-{issue.sequence_id}"


def _serialize_issue(issue: Issue, today: date) -> Dict[str, Any]:
    state_group = issue.state.group if issue.state else None
    return {
        "ref": _work_item_ref(issue),
        "id": str(issue.id),
        "name": issue.name,
        "project": issue.project.name,
        "state": issue.state.name if issue.state else None,
        "state_category": state_group,
        "priority": issue.priority,
        "assignees": [assignee.display_name for assignee in issue.assignees.all()],
        "labels": [label.name for label in issue.labels.all()],
        "start_date": issue.start_date.isoformat() if issue.start_date else None,
        "due_date": issue.target_date.isoformat() if issue.target_date else None,
        "deadline": deadline_status(issue.target_date, state_group, issue.completed_at, today),
        "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
    }


def _with_relations(queryset):
    return queryset.prefetch_related("assignees", "labels")


def resolve_work_item(scope: AssistantScope, work_item_ref: str) -> Issue:
    issues = _scoped_issues(scope)
    match = WORK_ITEM_REF_PATTERN.match(work_item_ref)
    issue = None
    if match:
        issue = issues.filter(project__identifier__iexact=match.group(1), sequence_id=int(match.group(2))).first()
    if issue is None:
        try:
            issue = issues.filter(id=work_item_ref).first()
        except Exception:
            issue = None
    if issue is None:
        issue = issues.filter(name__iexact=work_item_ref).first()
    if issue is None:
        raise ToolInputError(
            f"No accessible work item matches '{work_item_ref}'. Use search_work_items to find its reference."
        )
    return issue


def _overdue_filter(today: date) -> Q:
    return Q(target_date__lt=today) & ~Q(state__group__in=["completed", "cancelled"])


# ---------------------------------------------------------------------------
# tools
# ---------------------------------------------------------------------------


def list_projects(scope: AssistantScope, args: Dict[str, Any]) -> Dict[str, Any]:
    today = _today()
    result = []
    for project in _scoped_projects(scope).order_by("name"):
        issues = Issue.issue_objects.filter(project_id=project.id)
        result.append(
            {
                "identifier": project.identifier,
                "name": project.name,
                "open_work_items": issues.exclude(state__group__in=["completed", "cancelled"]).count(),
                "completed_work_items": issues.filter(state__group="completed").count(),
                "overdue_work_items": issues.filter(_overdue_filter(today)).count(),
            }
        )
    return {"today": today.isoformat(), "projects": result}


def search_work_items(scope: AssistantScope, args: Dict[str, Any]) -> Dict[str, Any]:
    today = _today()
    query = _optional_str(args, "query")
    project = _resolve_project(scope, _optional_str(args, "project"))
    state = _optional_str(args, "state")
    assignee = _optional_str(args, "assignee")
    label = _optional_str(args, "label")
    overdue_only = _optional_bool(args, "overdue_only")
    include_closed = _optional_bool(args, "include_closed")
    limit = _optional_int(args, "limit", default=25, minimum=1, maximum=MAX_LIST_RESULTS)

    issues = _scoped_issues(scope)
    if project:
        issues = issues.filter(project_id=project.id)
    if query:
        match = WORK_ITEM_REF_PATTERN.match(query)
        ref_filter = (
            Q(project__identifier__iexact=match.group(1), sequence_id=int(match.group(2))) if match else Q(pk__in=[])
        )
        issues = issues.filter(Q(name__icontains=query) | Q(description_stripped__icontains=query) | ref_filter)
    if state:
        issues = issues.filter(Q(state__name__icontains=state) | Q(state__group__iexact=state))
    if assignee:
        issues = issues.filter(
            Q(assignees__display_name__icontains=assignee)
            | Q(assignees__first_name__icontains=assignee)
            | Q(assignees__last_name__icontains=assignee)
            | Q(assignees__email__icontains=assignee)
        )
    if label:
        issues = issues.filter(labels__name__icontains=label)
    if overdue_only:
        issues = issues.filter(_overdue_filter(today))
    elif not include_closed:
        issues = issues.exclude(state__group__in=["completed", "cancelled"])

    issues = issues.distinct()
    total = issues.count()
    items = _with_relations(issues.order_by("target_date", "-updated_at"))[:limit]
    return {
        "today": today.isoformat(),
        "total_matches": total,
        "returned": min(total, limit),
        "work_items": [_serialize_issue(issue, today) for issue in items],
    }


def get_work_item(scope: AssistantScope, args: Dict[str, Any]) -> Dict[str, Any]:
    today = _today()
    work_item_ref = _optional_str(args, "work_item")
    if not work_item_ref:
        raise ToolInputError("'work_item' is required (a reference such as IAT-12, an id, or the exact name).")
    issue = _with_relations(_scoped_issues(scope)).get(pk=resolve_work_item(scope, work_item_ref).pk)

    details = _serialize_issue(issue, today)
    description = (issue.description_stripped or "").strip()
    details["description"] = description[:MAX_DESCRIPTION_CHARS] + (
        "…" if len(description) > MAX_DESCRIPTION_CHARS else ""
    )
    details["created_at"] = issue.created_at.isoformat()
    details["created_by"] = issue.created_by.display_name if issue.created_by else None
    details["completed_at"] = issue.completed_at.isoformat() if issue.completed_at else None
    details["parent"] = _work_item_ref(issue.parent) if issue.parent_id and issue.parent else None
    details["sub_work_items"] = [
        {
            "ref": _work_item_ref(child),
            "name": child.name,
            "state": child.state.name if child.state else None,
            "deadline": deadline_status(
                child.target_date, child.state.group if child.state else None, child.completed_at, today
            ),
        }
        for child in _scoped_issues(scope).filter(parent_id=issue.id).order_by("sequence_id")
    ]
    details["cycles"] = list(CycleIssue.objects.filter(issue_id=issue.id).values_list("cycle__name", flat=True))
    details["modules"] = list(ModuleIssue.objects.filter(issue_id=issue.id).values_list("module__name", flat=True))
    details["history"] = [
        {
            "at": activity.created_at.isoformat(),
            "by": activity.actor.display_name if activity.actor else None,
            "action": activity.verb,
            "field": activity.field,
            "from": activity.old_value,
            "to": activity.new_value,
        }
        for activity in IssueActivity.objects.filter(issue_id=issue.id)
        .exclude(field="comment")
        .select_related("actor")
        .order_by("-created_at")[:MAX_ACTIVITIES]
    ]
    details["comments"] = [
        {
            "at": comment.created_at.isoformat(),
            "by": comment.actor.display_name if comment.actor else None,
            "text": (comment.comment_stripped or "").strip()[:1000],
        }
        for comment in IssueComment.objects.filter(issue_id=issue.id)
        .select_related("actor")
        .order_by("-created_at")[:MAX_COMMENTS]
    ]
    return {"today": today.isoformat(), "work_item": details}


def project_progress(scope: AssistantScope, args: Dict[str, Any]) -> Dict[str, Any]:
    today = _today()
    project = _resolve_project(scope, _optional_str(args, "project"))
    if not project:
        raise ToolInputError("'project' is required. Call list_projects to see the projects you can query.")
    issues = Issue.issue_objects.filter(project_id=project.id).select_related("state", "project")

    columns = []
    for state in project.project_state.filter(deleted_at__isnull=True).exclude(group="triage").order_by("sequence"):
        columns.append(
            {"state": state.name, "category": state.group, "work_items": issues.filter(state_id=state.id).count()}
        )
    total = issues.exclude(state__group="cancelled").count()
    completed = issues.filter(state__group="completed").count()
    overdue = _with_relations(issues.filter(_overdue_filter(today)).order_by("target_date"))

    active_cycles = []
    for cycle in Cycle.objects.filter(
        project_id=project.id, archived_at__isnull=True, start_date__date__lte=today, end_date__date__gte=today
    ):
        cycle_issues = issues.filter(issue_cycle__cycle_id=cycle.id, issue_cycle__deleted_at__isnull=True)
        active_cycles.append(
            {
                "name": cycle.name,
                "ends_on": cycle.end_date.date().isoformat() if cycle.end_date else None,
                "work_items": cycle_issues.count(),
                "completed": cycle_issues.filter(state__group="completed").count(),
            }
        )

    modules = []
    for module in Module.objects.filter(project_id=project.id, archived_at__isnull=True).order_by("name"):
        module_issues = issues.filter(issue_module__module_id=module.id, issue_module__deleted_at__isnull=True)
        modules.append(
            {
                "name": module.name,
                "status": module.status,
                "target_date": module.target_date.isoformat() if module.target_date else None,
                "work_items": module_issues.count(),
                "completed": module_issues.filter(state__group="completed").count(),
            }
        )

    return {
        "today": today.isoformat(),
        "project": {"identifier": project.identifier, "name": project.name},
        "columns": columns,
        "total_work_items_excluding_cancelled": total,
        "completed": completed,
        "completion_percent": round(completed * 100 / total, 1) if total else None,
        "unassigned_open_work_items": issues.exclude(state__group__in=["completed", "cancelled"])
        .filter(assignees__isnull=True)
        .count(),
        "without_due_date_open_work_items": issues.exclude(state__group__in=["completed", "cancelled"])
        .filter(target_date__isnull=True)
        .count(),
        "overdue_count": overdue.count(),
        "overdue": [_serialize_issue(issue, today) for issue in overdue[:20]],
        "active_cycles": active_cycles,
        "modules": modules,
    }


def deadline_report(scope: AssistantScope, args: Dict[str, Any]) -> Dict[str, Any]:
    today = _today()
    project = _resolve_project(scope, _optional_str(args, "project"))
    assignee = _optional_str(args, "assignee")
    issues = _scoped_issues(scope).filter(target_date__isnull=False)
    if project:
        issues = issues.filter(project_id=project.id)
    if assignee:
        issues = issues.filter(
            Q(assignees__display_name__icontains=assignee)
            | Q(assignees__first_name__icontains=assignee)
            | Q(assignees__last_name__icontains=assignee)
            | Q(assignees__email__icontains=assignee)
        ).distinct()

    overdue, completed_late, completed_on_time = [], [], 0
    by_assignee: Dict[str, Dict[str, int]] = {}
    for issue in _with_relations(issues.order_by("target_date")):
        state_group = issue.state.group if issue.state else None
        status = deadline_status(issue.target_date, state_group, issue.completed_at, today)
        names = [assignee.display_name for assignee in issue.assignees.all()] or ["(unassigned)"]
        for name in names:
            by_assignee.setdefault(name, {"overdue": 0, "completed_late": 0, "completed_on_time": 0})
        if status["status"] == "overdue":
            overdue.append(_serialize_issue(issue, today))
            for name in names:
                by_assignee[name]["overdue"] += 1
        elif status["status"] == "completed_late":
            completed_late.append(_serialize_issue(issue, today))
            for name in names:
                by_assignee[name]["completed_late"] += 1
        elif status["status"] == "completed_on_time":
            completed_on_time += 1
            for name in names:
                by_assignee[name]["completed_on_time"] += 1

    overdue.sort(key=lambda item: -item["deadline"].get("days_late", 0))
    return {
        "today": today.isoformat(),
        "project": project.name if project else "all accessible projects",
        "overdue_count": len(overdue),
        "completed_late_count": len(completed_late),
        "completed_on_time_count": completed_on_time,
        "overdue": overdue[:MAX_LIST_RESULTS],
        "completed_late": completed_late[:MAX_LIST_RESULTS],
        "by_assignee": by_assignee,
    }


def member_workload(scope: AssistantScope, args: Dict[str, Any]) -> Dict[str, Any]:
    today = _today()
    project = _resolve_project(scope, _optional_str(args, "project"))
    issues = _scoped_issues(scope)
    if project:
        issues = issues.filter(project_id=project.id)
    since = today.toordinal() - 30

    workload: Dict[str, Dict[str, int]] = {}
    for issue in _with_relations(issues):
        group = issue.state.group if issue.state else None
        for assignee in issue.assignees.all():
            entry = workload.setdefault(
                assignee.display_name, {"open": 0, "overdue": 0, "in_progress": 0, "completed_last_30_days": 0}
            )
            if group in ("completed", "cancelled"):
                if group == "completed" and issue.completed_at and issue.completed_at.date().toordinal() >= since:
                    entry["completed_last_30_days"] += 1
                continue
            entry["open"] += 1
            if group == "started":
                entry["in_progress"] += 1
            if issue.target_date and issue.target_date < today:
                entry["overdue"] += 1
    return {
        "today": today.isoformat(),
        "project": project.name if project else "all accessible projects",
        "members": workload,
    }


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------

_PROJECT_PROPERTY = {
    "type": "string",
    "description": "Project identifier (e.g. IAT) or name. Omit to cover every accessible project.",
}
_ASSIGNEE_PROPERTY = {"type": "string", "description": "Part of the assignee's display name, name or email."}

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "list_projects",
        "description": (
            "List the projects the user can query, with counts of open, completed and overdue work items. "
            "Call this first when the user does not name a project or when a project name is ambiguous."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "search_work_items",
        "description": (
            "Search work items (tasks). Matches the query against the name, description and reference (e.g. IAT-12). "
            "Returns state, assignees, labels, dates and a computed deadline verdict for each. "
            "Closed (completed or cancelled) items are excluded unless include_closed is true."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Words from the title or description, or a reference."},
                "project": _PROJECT_PROPERTY,
                "state": {"type": "string", "description": "Column/state name, or a category such as 'started'."},
                "assignee": _ASSIGNEE_PROPERTY,
                "label": {"type": "string", "description": "Label name."},
                "overdue_only": {"type": "boolean", "description": "Only open items past their due date."},
                "include_closed": {"type": "boolean", "description": "Also return completed and cancelled items."},
                "limit": {"type": "integer", "description": f"Maximum results (1-{MAX_LIST_RESULTS}, default 25)."},
            },
        },
    },
    {
        "name": "get_work_item",
        "description": (
            "Full details of one work item: description, deadline verdict, sub-items, cycles, modules, "
            "change history (state changes with dates and authors) and recent comments."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "work_item": {
                    "type": "string",
                    "description": "Reference such as IAT-12 (preferred), the work item id, or its exact name.",
                }
            },
            "required": ["work_item"],
        },
    },
    {
        "name": "project_progress",
        "description": (
            "Progress of one project: work items per column, completion percentage, overdue items, "
            "unassigned and undated open items, active cycles and modules."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"project": {**_PROJECT_PROPERTY, "description": "Project identifier (e.g. IAT) or name."}},
            "required": ["project"],
        },
    },
    {
        "name": "deadline_report",
        "description": (
            "Deadline compliance: open items past their due date, items completed after their due date, "
            "items completed on time, and the same counts per assignee. Use it for any question about delays."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"project": _PROJECT_PROPERTY, "assignee": _ASSIGNEE_PROPERTY},
        },
    },
    {
        "name": "member_workload",
        "description": "Per assignee: open, in-progress and overdue items, and items completed in the last 30 days.",
        "input_schema": {"type": "object", "properties": {"project": _PROJECT_PROPERTY}},
    },
]

TOOL_HANDLERS: Dict[str, Callable[[AssistantScope, Dict[str, Any]], Dict[str, Any]]] = {
    "list_projects": list_projects,
    "search_work_items": search_work_items,
    "get_work_item": get_work_item,
    "project_progress": project_progress,
    "deadline_report": deadline_report,
    "member_workload": member_workload,
}


def run_tool(scope: AssistantScope, name: str, args: Any) -> str:
    """Execute a tool and return its JSON result. Raises ToolInputError for bad input."""
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        raise ToolInputError(f"Unknown tool '{name}'.")
    if not isinstance(args, dict):
        raise ToolInputError("Tool input must be a JSON object.")
    return json.dumps(handler(scope, args), ensure_ascii=False, default=str)
