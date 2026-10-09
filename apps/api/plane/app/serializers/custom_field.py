# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

# Module imports
from plane.db.models import CustomField, CustomFieldOption, IssueCustomFieldValue, ProjectCustomField

from .base import BaseSerializer


class CustomFieldOptionSerializer(BaseSerializer):
    class Meta:
        model = CustomFieldOption
        fields = ["id", "name", "color", "sort_order"]
        read_only_fields = fields


class CustomFieldSerializer(BaseSerializer):
    options = serializers.SerializerMethodField()

    class Meta:
        model = CustomField
        fields = [
            "id",
            "name",
            "description",
            "field_type",
            "number_precision",
            "options",
            "workspace_id",
            "created_by",
            "created_at",
        ]
        read_only_fields = fields

    @extend_schema_field(CustomFieldOptionSerializer(many=True))
    def get_options(self, field):
        # options are prefetched (non-deleted, ordered) by the views
        return CustomFieldOptionSerializer(field.options.all(), many=True).data


class ProjectCustomFieldSerializer(BaseSerializer):
    custom_field = CustomFieldSerializer(read_only=True)

    class Meta:
        model = ProjectCustomField
        fields = ["id", "custom_field", "custom_field_id", "project_id", "sort_order"]
        read_only_fields = fields


class IssueCustomFieldValueSerializer(BaseSerializer):
    class Meta:
        model = IssueCustomFieldValue
        fields = ["issue_id", "custom_field_id", "value", "updated_at"]
        read_only_fields = fields
