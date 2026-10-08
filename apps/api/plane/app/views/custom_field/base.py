# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import time
from typing import Any, Dict, List, Optional

# Django imports
from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from django.utils import timezone

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers import (
    CustomFieldSerializer,
    IssueCustomFieldValueSerializer,
    ProjectCustomFieldSerializer,
)
from plane.db.models import (
    CustomField,
    CustomFieldOption,
    CustomFieldType,
    Issue,
    IssueActivity,
    IssueCustomFieldValue,
    ProjectCustomField,
    Workspace,
)
from plane.utils.custom_field import (
    CustomFieldValueError,
    clean_custom_field_value,
    display_custom_field_value,
)

from ..base import BaseAPIView

SELECT_TYPES = (CustomFieldType.SINGLE_SELECT, CustomFieldType.MULTI_SELECT)
MAX_OPTIONS = 100


def _fields_queryset():
    return CustomField.objects.prefetch_related(
        Prefetch("options", queryset=CustomFieldOption.objects.order_by("sort_order"))
    )


def _error(message: str, status_code=status.HTTP_400_BAD_REQUEST) -> Response:
    return Response({"error": message}, status=status_code)


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


class WorkspaceCustomFieldEndpoint(BaseAPIView):
    """The organisation's library of custom fields."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug):
        fields = _fields_queryset().filter(workspace__slug=slug)
        return Response(CustomFieldSerializer(fields, many=True).data, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def post(self, request, slug):
        name = request.data.get("name")
        field_type = request.data.get("field_type")
        if not isinstance(name, str) or not name.strip():
            return _error("A name is required.")
        if field_type not in CustomFieldType.values:
            return _error("Unknown field type.")
        precision = request.data.get("number_precision", 0)
        if isinstance(precision, bool) or not isinstance(precision, int) or not 0 <= precision <= 6:
            return _error("number_precision must be an integer between 0 and 6.")
        options = _parse_options(request.data.get("options", []))
        if options is None:
            return _error("Options must be a list of unique, non-empty names.")
        if field_type in SELECT_TYPES and not options:
            return _error("A list field needs at least one option.")

        workspace = Workspace.objects.get(slug=slug)
        try:
            with transaction.atomic():
                field = CustomField.objects.create(
                    workspace=workspace,
                    name=name.strip()[:255],
                    description=str(request.data.get("description") or "")[:2000],
                    field_type=field_type,
                    number_precision=precision,
                )
                if field_type in SELECT_TYPES:
                    _sync_options(field, options)
        except IntegrityError:
            return _error("A custom field with this name already exists.")
        return Response(CustomFieldSerializer(_fields_queryset().get(pk=field.pk)).data, status=status.HTTP_201_CREATED)


class WorkspaceCustomFieldDetailEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def patch(self, request, slug, pk):
        field = _fields_queryset().get(workspace__slug=slug, pk=pk)
        update_fields = []
        if "name" in request.data:
            name = request.data["name"]
            if not isinstance(name, str) or not name.strip():
                return _error("A name is required.")
            field.name = name.strip()[:255]
            update_fields.append("name")
        if "description" in request.data:
            field.description = str(request.data["description"] or "")[:2000]
            update_fields.append("description")
        if "number_precision" in request.data:
            precision = request.data["number_precision"]
            if isinstance(precision, bool) or not isinstance(precision, int) or not 0 <= precision <= 6:
                return _error("number_precision must be an integer between 0 and 6.")
            field.number_precision = precision
            update_fields.append("number_precision")
        options = None
        if "options" in request.data:
            if field.field_type not in SELECT_TYPES:
                return _error("Only list fields have options.")
            options = _parse_options(request.data["options"])
            if not options:
                return _error("A list field needs at least one option, with unique names.")
        try:
            with transaction.atomic():
                if update_fields:
                    field.save(update_fields=[*update_fields, "updated_at"])
                if options is not None:
                    _sync_options(field, options)
        except IntegrityError:
            return _error("A custom field with this name already exists.")
        return Response(CustomFieldSerializer(_fields_queryset().get(pk=field.pk)).data, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def delete(self, request, slug, pk):
        field = CustomField.objects.get(workspace__slug=slug, pk=pk)
        now = timezone.now()
        with transaction.atomic():
            ProjectCustomField.objects.filter(custom_field=field).update(deleted_at=now)
            IssueCustomFieldValue.objects.filter(custom_field=field).update(deleted_at=now)
            CustomFieldOption.objects.filter(custom_field=field).update(deleted_at=now)
            field.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectCustomFieldEndpoint(BaseAPIView):
    """Custom fields added to a project."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def get(self, request, slug, project_id):
        project_fields = (
            ProjectCustomField.objects.filter(
                workspace__slug=slug, project_id=project_id, custom_field__deleted_at__isnull=True
            )
            .select_related("custom_field")
            .prefetch_related(
                Prefetch("custom_field__options", queryset=CustomFieldOption.objects.order_by("sort_order"))
            )
            .order_by("sort_order", "created_at")
        )
        return Response(ProjectCustomFieldSerializer(project_fields, many=True).data, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def post(self, request, slug, project_id):
        custom_field_id = request.data.get("custom_field_id")
        if not isinstance(custom_field_id, str):
            return _error("custom_field_id is required.")
        field = CustomField.objects.filter(workspace__slug=slug, pk=custom_field_id).first()
        if not field:
            return _error("Unknown custom field.", status.HTTP_404_NOT_FOUND)
        existing = ProjectCustomField.objects.filter(project_id=project_id, custom_field=field).first()
        if existing:
            return _error("This field is already in the project.")
        last = (
            ProjectCustomField.objects.filter(project_id=project_id)
            .order_by("-sort_order")
            .values_list("sort_order", flat=True)
            .first()
        )
        project_field = ProjectCustomField.objects.create(
            project_id=project_id, custom_field=field, sort_order=(last or 0) + 1000
        )
        project_field = (
            ProjectCustomField.objects.select_related("custom_field")
            .prefetch_related(
                Prefetch("custom_field__options", queryset=CustomFieldOption.objects.order_by("sort_order"))
            )
            .get(pk=project_field.pk)
        )
        return Response(ProjectCustomFieldSerializer(project_field).data, status=status.HTTP_201_CREATED)


class ProjectCustomFieldDetailEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def delete(self, request, slug, project_id, custom_field_id):
        # The values stay stored: adding the field back to the project shows them again.
        ProjectCustomField.objects.filter(project_id=project_id, custom_field_id=custom_field_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectCustomFieldValueEndpoint(BaseAPIView):
    """Values of the project's custom fields for the project's work items."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def get(self, request, slug, project_id):
        attached = ProjectCustomField.objects.filter(
            project_id=project_id, custom_field__deleted_at__isnull=True
        ).values_list("custom_field_id", flat=True)
        values = IssueCustomFieldValue.objects.filter(
            project_id=project_id, custom_field_id__in=attached, issue__deleted_at__isnull=True
        )
        issue_id = request.query_params.get("issue_id")
        if issue_id:
            values = values.filter(issue_id=issue_id)
        return Response(IssueCustomFieldValueSerializer(values, many=True).data, status=status.HTTP_200_OK)


class IssueCustomFieldValueEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def put(self, request, slug, project_id, issue_id, custom_field_id):
        if "value" not in request.data:
            return _error("'value' is required (null clears it).")
        is_attached = ProjectCustomField.objects.filter(
            project_id=project_id, custom_field_id=custom_field_id, custom_field__deleted_at__isnull=True
        ).exists()
        if not is_attached:
            return _error("This field is not part of the project.", status.HTTP_404_NOT_FOUND)
        issue = Issue.issue_objects.get(project_id=project_id, pk=issue_id)
        field = _fields_queryset().get(pk=custom_field_id)
        try:
            value = clean_custom_field_value(field, request.data["value"])
        except CustomFieldValueError as error:
            return _error(str(error))

        current = IssueCustomFieldValue.objects.filter(issue=issue, custom_field=field).first()
        old_value = current.value if current else None
        if old_value == value:
            return Response(
                IssueCustomFieldValueSerializer(current).data if current else None, status=status.HTTP_200_OK
            )

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
                    issue=issue, custom_field=field, project_id=project_id, value=value
                )
            IssueActivity.objects.create(
                issue=issue,
                project_id=project_id,
                workspace_id=issue.workspace_id,
                actor=request.user,
                verb="updated",
                field="custom_field",
                old_value=display_custom_field_value(field, old_value),
                new_value=display_custom_field_value(field, value),
                comment=field.name,
                epoch=int(time.time()),
            )
        return Response(
            IssueCustomFieldValueSerializer(result).data
            if result
            else {"custom_field_id": str(field.id), "value": None},
            status=status.HTTP_200_OK,
        )
