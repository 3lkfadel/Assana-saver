# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.app.views import (
    IssueCustomFieldValueEndpoint,
    ProjectCustomFieldDetailEndpoint,
    ProjectCustomFieldEndpoint,
    ProjectCustomFieldValueEndpoint,
    WorkspaceCustomFieldDetailEndpoint,
    WorkspaceCustomFieldEndpoint,
)

urlpatterns = [
    path("workspaces/<str:slug>/custom-fields/", WorkspaceCustomFieldEndpoint.as_view(), name="custom-fields"),
    path(
        "workspaces/<str:slug>/custom-fields/<uuid:pk>/",
        WorkspaceCustomFieldDetailEndpoint.as_view(),
        name="custom-field-detail",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/custom-fields/",
        ProjectCustomFieldEndpoint.as_view(),
        name="project-custom-fields",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/custom-fields/<uuid:custom_field_id>/",
        ProjectCustomFieldDetailEndpoint.as_view(),
        name="project-custom-field-detail",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/custom-field-values/",
        ProjectCustomFieldValueEndpoint.as_view(),
        name="project-custom-field-values",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/issues/<uuid:issue_id>/custom-fields/<uuid:custom_field_id>/",
        IssueCustomFieldValueEndpoint.as_view(),
        name="issue-custom-field-value",
    ),
]
