# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Custom fields (« champs personnalisés »).

A field is defined once in the organisation's library (``CustomField``), added to the projects
that use it (``ProjectCustomField``) and holds one value per task (``IssueCustomFieldValue``).
"""

# Django imports
from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models import Q

# Module imports
from .base import BaseModel
from .project import ProjectBaseModel


class CustomFieldType(models.TextChoices):
    TEXT = "text", "Text"
    NUMBER = "number", "Number"
    DATE = "date", "Date"
    SINGLE_SELECT = "single_select", "Single select"
    MULTI_SELECT = "multi_select", "Multi select"
    PEOPLE = "people", "People"


class CustomField(BaseModel):
    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="custom_fields")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    field_type = models.CharField(max_length=30, choices=CustomFieldType.choices)
    # Decimal places shown for number fields
    number_precision = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(6)])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                condition=Q(deleted_at__isnull=True),
                name="custom_field_unique_workspace_name_when_not_deleted",
            )
        ]
        verbose_name = "Custom Field"
        verbose_name_plural = "Custom Fields"
        db_table = "custom_fields"
        ordering = ("name",)

    def __str__(self):
        return f"{self.name} ({self.field_type})"


class CustomFieldOption(BaseModel):
    custom_field = models.ForeignKey(CustomField, on_delete=models.CASCADE, related_name="options")
    name = models.CharField(max_length=255)
    color = models.CharField(max_length=255, blank=True)
    sort_order = models.FloatField(default=65535)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["custom_field", "name"],
                condition=Q(deleted_at__isnull=True),
                name="custom_field_option_unique_name_when_not_deleted",
            )
        ]
        verbose_name = "Custom Field Option"
        verbose_name_plural = "Custom Field Options"
        db_table = "custom_field_options"
        ordering = ("sort_order",)

    def __str__(self):
        return self.name


class ProjectCustomField(ProjectBaseModel):
    custom_field = models.ForeignKey(CustomField, on_delete=models.CASCADE, related_name="project_custom_fields")
    sort_order = models.FloatField(default=65535)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "custom_field"],
                condition=Q(deleted_at__isnull=True),
                name="project_custom_field_unique_when_not_deleted",
            )
        ]
        verbose_name = "Project Custom Field"
        verbose_name_plural = "Project Custom Fields"
        db_table = "project_custom_fields"
        ordering = ("sort_order",)


class IssueCustomFieldValue(ProjectBaseModel):
    issue = models.ForeignKey("db.Issue", on_delete=models.CASCADE, related_name="custom_field_values")
    custom_field = models.ForeignKey(CustomField, on_delete=models.CASCADE, related_name="values")
    # text: str · number: float · date: "YYYY-MM-DD" · single_select: option id
    # multi_select: [option ids] · people: [user ids]
    value = models.JSONField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["issue", "custom_field"],
                condition=Q(deleted_at__isnull=True),
                name="issue_custom_field_value_unique_when_not_deleted",
            )
        ]
        verbose_name = "Issue Custom Field Value"
        verbose_name_plural = "Issue Custom Field Values"
        db_table = "issue_custom_field_values"
