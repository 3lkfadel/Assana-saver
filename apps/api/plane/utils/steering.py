# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Rules of the steering record of a work item (cahier des charges §4)."""

# Python imports
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

# Django imports
from django.utils import timezone

# Module imports
from plane.db.models import (
    CLOSED_STEERING_STATUSES,
    Entity,
    Issue,
    IssueAssignee,
    IssueSteering,
    SteeringCategory,
    SteeringRiskNature,
    SteeringStatus,
    SteeringWaitingFor,
    User,
    WorkspaceMember,
)

TEXT_LIMITS = {"risk_description": 1000, "closure_comment": 2000, "situation": 5000}
DATE_FIELDS = ("risk_effective_date", "closure_date")
CHOICE_FIELDS = {
    "status": SteeringStatus.values,
    "waiting_for": SteeringWaitingFor.values,
    "risk_nature": SteeringRiskNature.values,
}
REFERENCE_FIELDS = ("entity_id", "category_id", "supervisor_id", "approver_id")
RISK_FIELDS = ("risk_nature", "risk_effective_date", "risk_description")
EDITABLE_FIELDS = (*REFERENCE_FIELDS, *CHOICE_FIELDS, "progress", *DATE_FIELDS, *TEXT_LIMITS)


class SteeringValueError(ValueError):
    pass


def _clean_reference(key: str, value: Any, workspace_id) -> Optional[uuid.UUID]:
    if value in (None, ""):
        return None
    try:
        value = uuid.UUID(str(value))
    except ValueError:
        raise SteeringValueError(f"Unknown value for {key}.")
    if key == "entity_id":
        exists = Entity.objects.filter(workspace_id=workspace_id, pk=value).exists()
    elif key == "category_id":
        exists = SteeringCategory.objects.filter(workspace_id=workspace_id, pk=value).exists()
    else:
        exists = WorkspaceMember.objects.filter(workspace_id=workspace_id, member_id=value, is_active=True).exists()
    if not exists:
        raise SteeringValueError(f"Unknown value for {key}.")
    return value


def _clean_date(key: str, value: Any) -> Optional[date]:
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise SteeringValueError(f"{key} must be a YYYY-MM-DD date.")


def clean_steering_changes(data: Dict[str, Any], workspace_id) -> Dict[str, Any]:
    """Validate each submitted field on its own; the rules across fields come in ``apply``."""
    unknown = set(data) - set(EDITABLE_FIELDS)
    if unknown:
        raise SteeringValueError(f"Unknown fields: {', '.join(sorted(unknown))}.")
    changes: Dict[str, Any] = {}
    for key, value in data.items():
        if key in REFERENCE_FIELDS:
            changes[key] = _clean_reference(key, value, workspace_id)
        elif key in CHOICE_FIELDS:
            if value in (None, "") and key != "status":
                changes[key] = ""
            elif value not in CHOICE_FIELDS[key]:
                raise SteeringValueError(f"Unknown value for {key}.")
            else:
                changes[key] = value
        elif key == "progress":
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value != int(value):
                raise SteeringValueError("progress must be a whole number.")
            if not 0 <= value <= 100:
                raise SteeringValueError("progress must be between 0 and 100.")
            changes[key] = int(value)
        elif key in DATE_FIELDS:
            changes[key] = _clean_date(key, value)
        else:
            if value is None:
                value = ""
            if not isinstance(value, str):
                raise SteeringValueError(f"{key} must be text.")
            changes[key] = value.strip()[: TEXT_LIMITS[key]]
    return changes


def apply_steering_changes(
    steering: IssueSteering, changes: Dict[str, Any], now: Optional[datetime] = None
) -> List[Tuple[str, Any, Any]]:
    """
    Apply cleaned changes and the §4 rules, and return ``(field, old, new)`` for the history.
    Raises when the resulting record breaks a rule; ``steering`` must then be discarded.
    """
    now = now or timezone.now()
    tracked = (*EDITABLE_FIELDS,)
    before = {key: getattr(steering, key) for key in tracked}
    was_closed = steering.status in CLOSED_STEERING_STATUSES

    for key, value in changes.items():
        setattr(steering, key, value)

    if was_closed and any(getattr(steering, key) != before[key] for key in RISK_FIELDS):
        raise SteeringValueError("The risk can only change while the work item is open.")
    # 100 % is imposed when the work item is done; « En attente de » only exists while waiting.
    if steering.status == SteeringStatus.DONE:
        steering.progress = 100
    if steering.status != SteeringStatus.WAITING:
        steering.waiting_for = ""

    if steering.status == SteeringStatus.WAITING and not steering.waiting_for:
        raise SteeringValueError("A waiting work item needs « En attente de ».")
    if steering.status == SteeringStatus.DONE and not (steering.closure_date and steering.closure_comment):
        raise SteeringValueError("A done work item needs a closure date and a closure comment.")
    if steering.closure_date and steering.closure_date > timezone.localdate(now):
        raise SteeringValueError("The closure date cannot be in the future.")

    changed = [(key, before[key], getattr(steering, key)) for key in tracked if getattr(steering, key) != before[key]]
    changed_keys = {key for key, _, _ in changed}
    if changed_keys & {"status", "waiting_for"} or steering._state.adding:
        steering.waiting_since = now
    if "situation" in changed_keys:
        steering.situation_updated_at = now if steering.situation else None
    return changed


def display_steering_value(key: str, value: Any) -> Optional[str]:
    """History value: names for references (kept even if renamed later), codes for choices."""
    if value in (None, ""):
        return None
    if key == "entity_id":
        return Entity.all_objects.filter(pk=value).values_list("name", flat=True).first()
    if key == "category_id":
        return SteeringCategory.all_objects.filter(pk=value).values_list("name", flat=True).first()
    if key in ("supervisor_id", "approver_id"):
        return User.objects.filter(pk=value).values_list("display_name", flat=True).first()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def missing_steering_fields(issue: Issue, steering: Optional[IssueSteering], project_entity_id) -> List[str]:
    """Required §4 fields that the work item does not carry yet, conditional ones included."""
    missing = []
    if not ((steering and steering.entity_id) or project_entity_id):
        missing.append("entity")
    if not (steering and steering.category_id):
        missing.append("category")
    if not IssueAssignee.objects.filter(issue=issue).exists():
        missing.append("assignee")
    if not (steering and steering.supervisor_id):
        missing.append("supervisor")
    if not (steering and steering.approver_id):
        missing.append("approver")
    if not issue.priority or issue.priority == "none":
        missing.append("priority")
    if not issue.target_date:
        missing.append("target_date")
    if steering and steering.status == SteeringStatus.WAITING and not steering.waiting_for:
        missing.append("waiting_for")
    if steering and steering.status == SteeringStatus.DONE and not (steering.closure_date and steering.closure_comment):
        missing.append("closure")
    return missing
