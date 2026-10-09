# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.api.views import (
    CustomFieldDetailAPIEndpoint,
    CustomFieldListCreateAPIEndpoint,
    ProjectCustomFieldDetailAPIEndpoint,
    ProjectCustomFieldListCreateAPIEndpoint,
    ProjectCustomFieldValueListAPIEndpoint,
    WorkItemCustomFieldValueAPIEndpoint,
)

urlpatterns = [
    path(
        "workspaces/<str:slug>/custom-fields/",
        CustomFieldListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="custom-field-list",
    ),
    path(
        "workspaces/<str:slug>/custom-fields/<uuid:pk>/",
        CustomFieldDetailAPIEndpoint.as_view(http_method_names=["get", "patch"]),
        name="custom-field-detail",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/custom-fields/",
        ProjectCustomFieldListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="project-custom-field-list",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/custom-fields/<uuid:custom_field_id>/",
        ProjectCustomFieldDetailAPIEndpoint.as_view(http_method_names=["delete"]),
        name="project-custom-field-detail",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/custom-field-values/",
        ProjectCustomFieldValueListAPIEndpoint.as_view(http_method_names=["get"]),
        name="project-custom-field-values",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/work-items/<uuid:issue_id>/custom-fields/<uuid:custom_field_id>/",
        WorkItemCustomFieldValueAPIEndpoint.as_view(http_method_names=["put"]),
        name="work-item-custom-field-value",
    ),
]
