# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

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
from plane.db.models import CustomField, Issue, Workspace
from plane.utils.custom_field import CustomFieldValueError
from plane.utils.custom_field_service import (
    CustomFieldPayloadError,
    attach_custom_field,
    attached_project_fields,
    create_custom_field,
    delete_custom_field,
    detach_custom_field,
    fields_queryset,
    project_fields_queryset,
    project_values_queryset,
    set_issue_custom_field_value,
    update_custom_field,
)

from ..base import BaseAPIView


def _error(message: str, status_code=status.HTTP_400_BAD_REQUEST) -> Response:
    return Response({"error": message}, status=status_code)


class WorkspaceCustomFieldEndpoint(BaseAPIView):
    """The organisation's library of custom fields."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug):
        fields = fields_queryset().filter(workspace__slug=slug)
        return Response(CustomFieldSerializer(fields, many=True).data, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def post(self, request, slug):
        try:
            field = create_custom_field(Workspace.objects.get(slug=slug), request.data)
        except CustomFieldPayloadError as error:
            return _error(str(error))
        return Response(CustomFieldSerializer(field).data, status=status.HTTP_201_CREATED)


class WorkspaceCustomFieldDetailEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def patch(self, request, slug, pk):
        try:
            field = update_custom_field(fields_queryset().get(workspace__slug=slug, pk=pk), request.data)
        except CustomFieldPayloadError as error:
            return _error(str(error))
        return Response(CustomFieldSerializer(field).data, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def delete(self, request, slug, pk):
        delete_custom_field(CustomField.objects.get(workspace__slug=slug, pk=pk))
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectCustomFieldEndpoint(BaseAPIView):
    """Custom fields added to a project."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def get(self, request, slug, project_id):
        project_fields = project_fields_queryset(project_id).filter(workspace__slug=slug)
        return Response(ProjectCustomFieldSerializer(project_fields, many=True).data, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def post(self, request, slug, project_id):
        try:
            project_field = attach_custom_field(slug, project_id, request.data.get("custom_field_id"))
        except CustomField.DoesNotExist:
            return _error("Unknown custom field.", status.HTTP_404_NOT_FOUND)
        except CustomFieldPayloadError as error:
            return _error(str(error))
        return Response(ProjectCustomFieldSerializer(project_field).data, status=status.HTTP_201_CREATED)


class ProjectCustomFieldDetailEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def delete(self, request, slug, project_id, custom_field_id):
        detach_custom_field(project_id, custom_field_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectCustomFieldValueEndpoint(BaseAPIView):
    """Values of the project's custom fields for the project's work items."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def get(self, request, slug, project_id):
        values = project_values_queryset(project_id, request.query_params.get("issue_id"))
        return Response(IssueCustomFieldValueSerializer(values, many=True).data, status=status.HTTP_200_OK)


class IssueCustomFieldValueEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def put(self, request, slug, project_id, issue_id, custom_field_id):
        if "value" not in request.data:
            return _error("'value' is required (null clears it).")
        field = attached_project_fields(project_id).get(str(custom_field_id))
        if not field:
            return _error("This field is not part of the project.", status.HTTP_404_NOT_FOUND)
        issue = Issue.issue_objects.get(project_id=project_id, pk=issue_id)
        try:
            result = set_issue_custom_field_value(issue, field, request.data["value"], request.user)
        except CustomFieldValueError as error:
            return _error(str(error))
        return Response(
            IssueCustomFieldValueSerializer(result).data
            if result
            else {"custom_field_id": str(field.id), "value": None},
            status=status.HTTP_200_OK,
        )
