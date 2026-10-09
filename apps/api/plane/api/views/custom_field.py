# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Custom fields in the public API: the organisation's library, project fields and task values."""

# Third party imports
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiRequest, OpenApiResponse, inline_serializer
from rest_framework import serializers, status
from rest_framework.response import Response

# Module imports
from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers import (
    CustomFieldSerializer,
    IssueCustomFieldValueSerializer,
    ProjectCustomFieldSerializer,
)
from plane.db.models import CustomField, Issue, Workspace
from plane.utils.custom_field import CustomFieldValueError
from plane.utils.custom_field_service import (
    CustomFieldPayloadError,
    attach_custom_field,
    attached_project_fields,
    create_custom_field,
    detach_custom_field,
    fields_queryset,
    project_fields_queryset,
    project_values_queryset,
    set_issue_custom_field_value,
    update_custom_field,
)
from plane.utils.openapi import (
    INVALID_REQUEST_RESPONSE,
    DELETED_RESPONSE,
    PROJECT_ID_PARAMETER,
    custom_field_docs,
)

from .base import BaseAPIView

CUSTOM_FIELD_ID_PARAMETER = OpenApiParameter(
    name="custom_field_id", description="Custom field ID", required=True, type=OpenApiTypes.UUID, location="path"
)
FIELD_PK_PARAMETER = OpenApiParameter(
    name="pk", description="Custom field ID", required=True, type=OpenApiTypes.UUID, location="path"
)
WORK_ITEM_ID_PARAMETER = OpenApiParameter(
    name="issue_id", description="Work item ID", required=True, type=OpenApiTypes.UUID, location="path"
)

_OPTION_REQUEST = inline_serializer(
    name="CustomFieldOptionRequest",
    fields={
        "id": serializers.UUIDField(required=False, help_text="Keep an existing option (omit for a new one)"),
        "name": serializers.CharField(),
        "color": serializers.CharField(required=False),
    },
)
_FIELD_REQUEST = inline_serializer(
    name="CustomFieldRequest",
    fields={
        "name": serializers.CharField(),
        "description": serializers.CharField(required=False),
        "field_type": serializers.ChoiceField(
            choices=["text", "number", "date", "single_select", "multi_select", "people"],
            help_text="Cannot be changed after creation",
        ),
        "number_precision": serializers.IntegerField(required=False, min_value=0, max_value=6),
        "options": serializers.ListField(
            child=_OPTION_REQUEST,
            required=False,
            help_text="List fields only. On update, options left out are removed along with their values.",
        ),
    },
)
_VALUE_REQUEST = inline_serializer(
    name="CustomFieldValueRequest",
    fields={
        "value": serializers.JSONField(
            allow_null=True,
            help_text=(
                "text: string · number: number · date: 'YYYY-MM-DD' · single_select: option id · "
                "multi_select: [option ids] · people: [user ids] · null or empty clears the value"
            ),
        )
    },
)


def _error(message: str, status_code=status.HTTP_400_BAD_REQUEST) -> Response:
    return Response({"error": message}, status=status_code)


class CustomFieldListCreateAPIEndpoint(BaseAPIView):
    """The organisation's library of custom fields."""

    @custom_field_docs(
        operation_id="list_custom_fields",
        summary="List custom fields",
        description="List the fields of the organisation's library, with their options.",
        responses={200: OpenApiResponse(description="Custom fields", response=CustomFieldSerializer(many=True))},
    )
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug):
        fields = fields_queryset().filter(workspace__slug=slug)
        return Response(CustomFieldSerializer(fields, many=True).data, status=status.HTTP_200_OK)

    @custom_field_docs(
        operation_id="create_custom_field",
        summary="Create custom field",
        description="Add a field to the organisation's library. List fields need at least one option.",
        request=OpenApiRequest(request=_FIELD_REQUEST),
        responses={
            201: OpenApiResponse(description="Custom field created", response=CustomFieldSerializer),
            400: INVALID_REQUEST_RESPONSE,
        },
    )
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def post(self, request, slug):
        try:
            field = create_custom_field(Workspace.objects.get(slug=slug), request.data)
        except CustomFieldPayloadError as error:
            return _error(str(error))
        return Response(CustomFieldSerializer(field).data, status=status.HTTP_201_CREATED)


class CustomFieldDetailAPIEndpoint(BaseAPIView):
    @custom_field_docs(
        operation_id="retrieve_custom_field",
        summary="Retrieve custom field",
        parameters=[FIELD_PK_PARAMETER],
        responses={200: OpenApiResponse(description="Custom field", response=CustomFieldSerializer)},
    )
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug, pk):
        field = fields_queryset().get(workspace__slug=slug, pk=pk)
        return Response(CustomFieldSerializer(field).data, status=status.HTTP_200_OK)

    @custom_field_docs(
        operation_id="update_custom_field",
        summary="Update custom field",
        description="Rename a field, change its description or precision, or replace its options.",
        parameters=[FIELD_PK_PARAMETER],
        request=OpenApiRequest(request=_FIELD_REQUEST),
        responses={
            200: OpenApiResponse(description="Custom field updated", response=CustomFieldSerializer),
            400: INVALID_REQUEST_RESPONSE,
        },
    )
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def patch(self, request, slug, pk):
        try:
            field = update_custom_field(fields_queryset().get(workspace__slug=slug, pk=pk), request.data)
        except CustomFieldPayloadError as error:
            return _error(str(error))
        return Response(CustomFieldSerializer(field).data, status=status.HTTP_200_OK)


class ProjectCustomFieldListCreateAPIEndpoint(BaseAPIView):
    """Custom fields added to a project."""

    @custom_field_docs(
        operation_id="list_project_custom_fields",
        summary="List project custom fields",
        description="List the fields shown on the project's tasks, in display order.",
        parameters=[PROJECT_ID_PARAMETER],
        responses={
            200: OpenApiResponse(description="Project fields", response=ProjectCustomFieldSerializer(many=True))
        },
    )
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def get(self, request, slug, project_id):
        project_fields = project_fields_queryset(project_id).filter(workspace__slug=slug)
        return Response(ProjectCustomFieldSerializer(project_fields, many=True).data, status=status.HTTP_200_OK)

    @custom_field_docs(
        operation_id="add_project_custom_field",
        summary="Add custom field to project",
        description="Add a field of the organisation's library to the project, after its other fields.",
        parameters=[PROJECT_ID_PARAMETER],
        request=OpenApiRequest(
            request=inline_serializer(
                name="ProjectCustomFieldRequest", fields={"custom_field_id": serializers.UUIDField()}
            )
        ),
        responses={
            201: OpenApiResponse(description="Field added", response=ProjectCustomFieldSerializer),
            400: INVALID_REQUEST_RESPONSE,
        },
    )
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def post(self, request, slug, project_id):
        try:
            project_field = attach_custom_field(slug, project_id, request.data.get("custom_field_id"))
        except CustomField.DoesNotExist:
            return _error("Unknown custom field.", status.HTTP_404_NOT_FOUND)
        except CustomFieldPayloadError as error:
            return _error(str(error))
        return Response(ProjectCustomFieldSerializer(project_field).data, status=status.HTTP_201_CREATED)


class ProjectCustomFieldDetailAPIEndpoint(BaseAPIView):
    @custom_field_docs(
        operation_id="remove_project_custom_field",
        summary="Remove custom field from project",
        description="Hide the field on the project's tasks. Values are kept and come back if the field is added again.",
        parameters=[PROJECT_ID_PARAMETER, CUSTOM_FIELD_ID_PARAMETER],
        responses={204: DELETED_RESPONSE},
    )
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def delete(self, request, slug, project_id, custom_field_id):
        detach_custom_field(project_id, custom_field_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectCustomFieldValueListAPIEndpoint(BaseAPIView):
    @custom_field_docs(
        operation_id="list_project_custom_field_values",
        summary="List custom field values",
        description="Values of the project's fields for its tasks, optionally for a single task.",
        parameters=[
            PROJECT_ID_PARAMETER,
            OpenApiParameter(
                name="work_item_id", description="Only this task's values", required=False, type=OpenApiTypes.UUID
            ),
        ],
        responses={200: OpenApiResponse(description="Values", response=IssueCustomFieldValueSerializer(many=True))},
    )
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def get(self, request, slug, project_id):
        values = project_values_queryset(project_id, request.query_params.get("work_item_id"))
        return Response(IssueCustomFieldValueSerializer(values, many=True).data, status=status.HTTP_200_OK)


class WorkItemCustomFieldValueAPIEndpoint(BaseAPIView):
    @custom_field_docs(
        operation_id="set_work_item_custom_field_value",
        summary="Set custom field value",
        description=(
            "Set or clear a task's value for one of the project's fields. The change is kept in the task's history."
        ),
        parameters=[PROJECT_ID_PARAMETER, WORK_ITEM_ID_PARAMETER, CUSTOM_FIELD_ID_PARAMETER],
        request=OpenApiRequest(request=_VALUE_REQUEST),
        responses={
            200: OpenApiResponse(description="Value stored", response=IssueCustomFieldValueSerializer),
            400: INVALID_REQUEST_RESPONSE,
        },
    )
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def put(self, request, slug, project_id, issue_id, custom_field_id):
        if "value" not in request.data:
            return _error("'value' is required (null clears it).")
        field = attached_project_fields(project_id).get(str(custom_field_id))
        if not field:
            return _error("This field is not part of the project.", status.HTTP_404_NOT_FOUND)
        issue = Issue.issue_objects.get(workspace__slug=slug, project_id=project_id, pk=issue_id)
        try:
            result = set_issue_custom_field_value(issue, field, request.data["value"], request.user)
        except CustomFieldValueError as error:
            return _error(str(error))
        return Response(
            IssueCustomFieldValueSerializer(result).data
            if result
            else {"issue_id": str(issue.id), "custom_field_id": str(field.id), "value": None},
            status=status.HTTP_200_OK,
        )
