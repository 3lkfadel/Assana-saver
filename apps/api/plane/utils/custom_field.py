# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Validation and display of custom field values."""

# Python imports
from datetime import date
from typing import Any, Optional

# Module imports
from plane.db.models import CustomField, CustomFieldType, User, WorkspaceMember

MAX_TEXT_LENGTH = 5000


class CustomFieldValueError(ValueError):
    """Raised when a value does not match the field type."""


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == []


def clean_custom_field_value(field: CustomField, value: Any) -> Optional[Any]:
    """
    Normalise a raw value for ``field``. Returns ``None`` when the value is empty (the value is cleared).
    Raises ``CustomFieldValueError`` when the value is invalid for the field type.
    """
    if _is_empty(value):
        return None

    if field.field_type == CustomFieldType.TEXT:
        if not isinstance(value, str):
            raise CustomFieldValueError("Expected text.")
        value = value.strip()
        if len(value) > MAX_TEXT_LENGTH:
            raise CustomFieldValueError(f"Text is limited to {MAX_TEXT_LENGTH} characters.")
        return value or None

    if field.field_type == CustomFieldType.NUMBER:
        if isinstance(value, bool):
            raise CustomFieldValueError("Expected a number.")
        try:
            number = float(str(value).replace(",", "."))
        except ValueError as error:
            raise CustomFieldValueError("Expected a number.") from error
        if number != number or number in (float("inf"), float("-inf")):
            raise CustomFieldValueError("Expected a finite number.")
        return round(number, field.number_precision)

    if field.field_type == CustomFieldType.DATE:
        if not isinstance(value, str):
            raise CustomFieldValueError("Expected a date (YYYY-MM-DD).")
        try:
            return date.fromisoformat(value[:10]).isoformat()
        except ValueError as error:
            raise CustomFieldValueError("Expected a date (YYYY-MM-DD).") from error

    if field.field_type == CustomFieldType.SINGLE_SELECT:
        if not isinstance(value, str) or not field.options.filter(id=value).exists():
            raise CustomFieldValueError("Unknown option for this field.")
        return value

    if field.field_type == CustomFieldType.MULTI_SELECT:
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise CustomFieldValueError("Expected a list of options.")
        option_ids = list(dict.fromkeys(value))
        known = {str(option_id) for option_id in field.options.filter(id__in=option_ids).values_list("id", flat=True)}
        if len(known) != len(option_ids):
            raise CustomFieldValueError("Unknown option for this field.")
        return option_ids

    if field.field_type == CustomFieldType.PEOPLE:
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise CustomFieldValueError("Expected a list of people.")
        user_ids = list(dict.fromkeys(value))
        members = {
            str(member_id)
            for member_id in WorkspaceMember.objects.filter(
                workspace_id=field.workspace_id, member_id__in=user_ids, is_active=True
            ).values_list("member_id", flat=True)
        }
        if len(members) != len(user_ids):
            raise CustomFieldValueError("Every person must be a member of the organisation.")
        return user_ids

    raise CustomFieldValueError("Unsupported field type.")


def display_custom_field_value(field: CustomField, value: Any) -> str:
    """Human-readable value, used in the work item history."""
    if _is_empty(value):
        return ""
    if field.field_type in (CustomFieldType.SINGLE_SELECT, CustomFieldType.MULTI_SELECT):
        option_ids = value if isinstance(value, list) else [value]
        names = {
            str(option_id): name
            for option_id, name in field.options.filter(id__in=option_ids).values_list("id", "name")
        }
        return ", ".join(names.get(str(option_id), "") for option_id in option_ids)
    if field.field_type == CustomFieldType.NUMBER and isinstance(value, (int, float)):
        return f"{value:.{field.number_precision}f}"
    if field.field_type == CustomFieldType.PEOPLE:
        names = {
            str(user_id): name for user_id, name in User.objects.filter(id__in=value).values_list("id", "display_name")
        }
        return ", ".join(names.get(str(user_id), "") for user_id in value)
    return str(value)
