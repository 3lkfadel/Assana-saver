# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Custom field operations shared by the app API (session) and the public API v1 (API key).

The views only translate HTTP: every rule about definitions, options, project attachment and
values lives here, so both surfaces behave the same.
"""

# Python imports
import time
from typing import Any, Dict, List, Mapping, Optional

# Django imports
from django.db import IntegrityError, transaction
from django.db.models import Prefetch, QuerySet
from django.utils import timezone

# Module imports
from plane.db.models import (
    CustomField,
    CustomFieldOption,
    CustomFieldType,
    Issue,
    IssueActivity,
    IssueCustomFieldValue,
    ProjectCustomField,
    User,
    Workspace,
)
from plane.utils.custom_field import clean_custom_field_value, display_custom_field_value

SELECT_TYPES = (CustomFieldType.SINGLE_SELECT, CustomFieldType.MULTI_SELECT)
MAX_OPTIONS = 100


class CustomFieldPayloadError(ValueError):
    """Raised when a definition or an attachment request is invalid; the message is shown to the client."""


def fields_queryset() -> QuerySet:
    return CustomField.objects.prefetch_related(
        Prefetch("options", queryset=CustomFieldOption.objects.order_by("sort_order"))
    )


def project_fields_queryset(project_id) -> QuerySet:
    return (
        ProjectCustomField.objects.filter(project_id=project_id, custom_field__deleted_at__isnull=True)
        .select_related("custom_field")
        .prefetch_related(Prefetch("custom_field__options", queryset=CustomFieldOption.objects.order_by("sort_order")))
        .order_by("sort_order", "created_at")
    )


def _parse_options(raw_options: Any) -> Optional[List[Dict[str, str]]]:
    """Validate ``[{id?, name, color?}]``; returns None when invalid."""
    if not isinstance(raw_options, list) or len(raw_options) > MAX_OPTIONS:
        return None
    options, names = [], set()
    for raw in raw_options:
        if not isinstance(raw, dict) or not isinstance(raw.get("name"), str) or not raw["name"].strip():
            return None
        name = raw["name"].strip()[:255]
        if name.lower() in names:
            return None
        names.add(name.lower())
        option_id = raw.get("id")
        color = raw.get("color") if isinstance(raw.get("color"), str) else ""
        options.append({"id": option_id if isinstance(option_id, str) else None, "name": name, "color": color[:255]})
    return options


def _parse_precision(precision: Any) -> int:
    if isinstance(precision, bool) or not isinstance(precision, int) or not 0 <= precision <= 6:
        raise CustomFieldPayloadError("number_precision must be an integer between 0 and 6.")
    return precision


def _sync_options(field: CustomField, options: List[Dict[str, str]]) -> None:
    """Create, update and reorder options; options left out are removed, and so are their uses in values."""
    existing = {str(option.id): option for option in field.options.all()}
    kept_ids = set()
    for index, option in enumerate(options):
        current = existing.get(option["id"]) if option["id"] else None
        if current:
            current.name, current.color, current.sort_order = option["name"], option["color"], (index + 1) * 1000
            current.save(update_fields=["name", "color", "sort_order", "updated_at"])
            kept_ids.add(str(current.id))
        else:
            created = CustomFieldOption.objects.create(
                custom_field=field, name=option["name"], color=option["color"], sort_order=(index + 1) * 1000
            )
            kept_ids.add(str(created.id))

    removed_ids = set(existing) - kept_ids
    if not removed_ids:
        return
    CustomFieldOption.objects.filter(id__in=removed_ids).update(deleted_at=timezone.now())
    values = IssueCustomFieldValue.objects.filter(custom_field=field)
    if field.field_type == CustomFieldType.SINGLE_SELECT:
        values.filter(value__in=list(removed_ids)).update(deleted_at=timezone.now())
    else:
        for value in values:
            remaining = [option_id for option_id in (value.value or []) if option_id not in removed_ids]
            if remaining != value.value:
                if remaining:
                    value.value = remaining
                    value.save(update_fields=["value", "updated_at"])
                else:
                    value.delete()


def create_custom_field(workspace: Workspace, data: Mapping[str, Any]) -> CustomField:
    """Add a field to the organisation's library. Raises ``CustomFieldPayloadError``."""
    name = data.get("name")
    field_type = data.get("field_type")
    if not isinstance(name, str) or not name.strip():
        raise CustomFieldPayloadError("A name is required.")
    if field_type not in CustomFieldType.values:
        raise CustomFieldPayloadError("Unknown field type.")
    precision = _parse_precision(data.get("number_precision", 0))
    options = _parse_options(data.get("options", []))
    if options is None:
        raise CustomFieldPayloadError("Options must be a list of unique, non-empty names.")
    if field_type in SELECT_TYPES and not options:
        raise CustomFieldPayloadError("A list field needs at least one option.")

    try:
        with transaction.atomic():
            field = CustomField.objects.create(
                workspace=workspace,
                name=name.strip()[:255],
                description=str(data.get("description") or "")[:2000],
                field_type=field_type,
                number_precision=precision,
            )
            if field_type in SELECT_TYPES:
                _sync_options(field, options)
    except IntegrityError as error:
        raise CustomFieldPayloadError("A custom field with this name already exists.") from error
    return fields_queryset().get(pk=field.pk)


def update_custom_field(field: CustomField, data: Mapping[str, Any]) -> CustomField:
    """
    Rename, describe or reorder a field's options. The type cannot change. Options left out of
    ``options`` are removed, along with their uses in values. Raises ``CustomFieldPayloadError``.
    """
    update_fields = []
    if "name" in data:
        name = data["name"]
        if not isinstance(name, str) or not name.strip():
            raise CustomFieldPayloadError("A name is required.")
        field.name = name.strip()[:255]
        update_fields.append("name")
    if "description" in data:
        field.description = str(data["description"] or "")[:2000]
        update_fields.append("description")
    if "number_precision" in data:
        field.number_precision = _parse_precision(data["number_precision"])
        update_fields.append("number_precision")
    options = None
    if "options" in data:
        if field.field_type not in SELECT_TYPES:
            raise CustomFieldPayloadError("Only list fields have options.")
        options = _parse_options(data["options"])
        if not options:
            raise CustomFieldPayloadError("A list field needs at least one option, with unique names.")
    try:
        with transaction.atomic():
            if update_fields:
                field.save(update_fields=[*update_fields, "updated_at"])
            if options is not None:
                _sync_options(field, options)
    except IntegrityError as error:
        raise CustomFieldPayloadError("A custom field with this name already exists.") from error
    return fields_queryset().get(pk=field.pk)


def delete_custom_field(field: CustomField) -> None:
    """Remove a field from the library, from every project and every task."""
    now = timezone.now()
    with transaction.atomic():
        ProjectCustomField.objects.filter(custom_field=field).update(deleted_at=now)
        IssueCustomFieldValue.objects.filter(custom_field=field).update(deleted_at=now)
        CustomFieldOption.objects.filter(custom_field=field).update(deleted_at=now)
        field.delete()


def attach_custom_field(workspace_slug: str, project_id, custom_field_id: Any) -> ProjectCustomField:
    """Add a library field to a project, after the project's other fields. Raises ``CustomFieldPayloadError``."""
    if not isinstance(custom_field_id, str):
        raise CustomFieldPayloadError("custom_field_id is required.")
    field = CustomField.objects.filter(workspace__slug=workspace_slug, pk=custom_field_id).first()
    if not field:
        raise CustomField.DoesNotExist("Unknown custom field.")
    if ProjectCustomField.objects.filter(project_id=project_id, custom_field=field).exists():
        raise CustomFieldPayloadError("This field is already in the project.")
    last = (
        ProjectCustomField.objects.filter(project_id=project_id)
        .order_by("-sort_order")
        .values_list("sort_order", flat=True)
        .first()
    )
    project_field = ProjectCustomField.objects.create(
        project_id=project_id, custom_field=field, sort_order=(last or 0) + 1000
    )
    return project_fields_queryset(project_id).get(pk=project_field.pk)


def detach_custom_field(project_id, custom_field_id) -> None:
    # The values stay stored: adding the field back to the project shows them again.
    ProjectCustomField.objects.filter(project_id=project_id, custom_field_id=custom_field_id).delete()


def project_values_queryset(project_id, issue_id=None) -> QuerySet:
    """Values of the fields attached to the project, for its tasks that still exist."""
    attached = ProjectCustomField.objects.filter(
        project_id=project_id, custom_field__deleted_at__isnull=True
    ).values_list("custom_field_id", flat=True)
    values = IssueCustomFieldValue.objects.filter(
        project_id=project_id, custom_field_id__in=attached, issue__deleted_at__isnull=True
    )
    if issue_id:
        values = values.filter(issue_id=issue_id)
    return values


def attached_project_fields(project_id) -> Dict[str, CustomField]:
    """Fields attached to the project, by id, with their options prefetched."""
    attached_ids = ProjectCustomField.objects.filter(
        project_id=project_id, custom_field__deleted_at__isnull=True
    ).values_list("custom_field_id", flat=True)
    return {str(field.id): field for field in fields_queryset().filter(pk__in=attached_ids)}


def set_issue_custom_field_value(
    issue: Issue, field: CustomField, raw_value: Any, actor: User
) -> Optional[IssueCustomFieldValue]:
    """
    Set (or clear, with an empty value) the task's value for ``field`` and record it in the task's
    history. The field must be attached to the task's project. Returns the stored value, or None when
    cleared. Raises ``CustomFieldValueError`` when the value does not match the field type.
    """
    value = clean_custom_field_value(field, raw_value)
    current = IssueCustomFieldValue.objects.filter(issue=issue, custom_field=field).first()
    old_value = current.value if current else None
    if old_value == value:
        return current

    with transaction.atomic():
        if value is None:
            if current:
                current.delete()
            result = None
        elif current:
            current.value = value
            current.save(update_fields=["value", "updated_at"])
            result = current
        else:
            result = IssueCustomFieldValue.objects.create(
                issue=issue, custom_field=field, project_id=issue.project_id, value=value
            )
        IssueActivity.objects.create(
            issue=issue,
            project_id=issue.project_id,
            workspace_id=issue.workspace_id,
            actor=actor,
            verb="updated",
            field="custom_field",
            old_value=display_custom_field_value(field, old_value),
            new_value=display_custom_field_value(field, value),
            comment=field.name,
            epoch=int(time.time()),
        )
    return result
