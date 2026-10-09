# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.app.views import (
    IssueSteeringEndpoint,
    ProjectSteeringEndpoint,
    SteeringBootstrapEndpoint,
    SteeringBranchDetailEndpoint,
    SteeringBranchEndpoint,
    SteeringCategoryDetailEndpoint,
    SteeringCategoryEndpoint,
    SteeringEntityDetailEndpoint,
    SteeringEntityEndpoint,
    SteeringProfileDetailEndpoint,
    SteeringProfileEndpoint,
    SteeringReferentialEndpoint,
)

urlpatterns = [
    path("workspaces/<str:slug>/steering/", SteeringReferentialEndpoint.as_view(), name="steering-referential"),
    path(
        "workspaces/<str:slug>/steering/bootstrap/",
        SteeringBootstrapEndpoint.as_view(),
        name="steering-bootstrap",
    ),
    path("workspaces/<str:slug>/steering/branches/", SteeringBranchEndpoint.as_view(), name="steering-branches"),
    path(
        "workspaces/<str:slug>/steering/branches/<uuid:pk>/",
        SteeringBranchDetailEndpoint.as_view(),
        name="steering-branch-detail",
    ),
    path("workspaces/<str:slug>/steering/entities/", SteeringEntityEndpoint.as_view(), name="steering-entities"),
    path(
        "workspaces/<str:slug>/steering/entities/<uuid:pk>/",
        SteeringEntityDetailEndpoint.as_view(),
        name="steering-entity-detail",
    ),
    path(
        "workspaces/<str:slug>/steering/categories/",
        SteeringCategoryEndpoint.as_view(),
        name="steering-categories",
    ),
    path(
        "workspaces/<str:slug>/steering/categories/<uuid:pk>/",
        SteeringCategoryDetailEndpoint.as_view(),
        name="steering-category-detail",
    ),
    path("workspaces/<str:slug>/steering/profiles/", SteeringProfileEndpoint.as_view(), name="steering-profiles"),
    path(
        "workspaces/<str:slug>/steering/profiles/<uuid:pk>/",
        SteeringProfileDetailEndpoint.as_view(),
        name="steering-profile-detail",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/steering/",
        ProjectSteeringEndpoint.as_view(),
        name="project-steering",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/issues/<uuid:issue_id>/steering/",
        IssueSteeringEndpoint.as_view(),
        name="issue-steering",
    ),
]
