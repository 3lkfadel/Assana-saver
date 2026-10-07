# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Infinity Planning has no cycles, modules, estimates or Guest role."""

from unittest.mock import patch

import pytest
from rest_framework import status

from plane.db.models import (
    Estimate,
    Project,
    ProjectMember,
    User,
    WorkspaceMember,
    WorkspaceMemberInvite,
)
from plane.utils.disabled_features import ESTIMATES_DISABLED_ERROR, GUEST_ROLE_DISABLED_ERROR


@pytest.fixture
def project(workspace, create_user):
    project = Project.objects.create(name="Pilot", identifier="PIL", workspace=workspace)
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def other_member(workspace):
    user = User.objects.create(email="colleague@infinity-africa.com", username="colleague")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    return user


@pytest.mark.contract
class TestGuestRoleDisabled:
    @pytest.mark.django_db
    @patch("plane.app.views.workspace.invite.workspace_invitation.delay")
    def test_workspace_invite_with_guest_role_is_refused(self, _mock_delay, session_client, workspace):
        url = f"/api/workspaces/{workspace.slug}/invitations/"
        emails = [{"email": "guest@infinity-africa.com", "role": 5}]

        response = session_client.post(url, {"emails": emails}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"] == GUEST_ROLE_DISABLED_ERROR
        assert not WorkspaceMemberInvite.objects.filter(workspace=workspace).exists()

    @pytest.mark.django_db
    @patch("plane.app.views.workspace.invite.workspace_invitation.delay")
    def test_workspace_invite_defaults_to_member_role(self, _mock_delay, session_client, workspace):
        url = f"/api/workspaces/{workspace.slug}/invitations/"

        response = session_client.post(url, {"emails": [{"email": "new@infinity-africa.com"}]}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert WorkspaceMemberInvite.objects.get(workspace=workspace).role == 15

    @pytest.mark.django_db
    def test_workspace_invite_cannot_be_changed_to_guest(self, session_client, workspace):
        invite = WorkspaceMemberInvite.objects.create(
            workspace=workspace, email="new@infinity-africa.com", token="token", role=15
        )
        url = f"/api/workspaces/{workspace.slug}/invitations/{invite.id}/"

        response = session_client.patch(url, {"role": 5}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        invite.refresh_from_db()
        assert invite.role == 15

    @pytest.mark.django_db
    def test_workspace_member_cannot_become_guest(self, session_client, workspace, other_member):
        member = WorkspaceMember.objects.get(workspace=workspace, member=other_member)
        url = f"/api/workspaces/{workspace.slug}/members/{member.id}/"

        response = session_client.patch(url, {"role": 5}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"] == GUEST_ROLE_DISABLED_ERROR
        member.refresh_from_db()
        assert member.role == 15

    @pytest.mark.django_db
    def test_project_member_cannot_be_added_as_guest(self, session_client, workspace, project, other_member):
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/members/"

        response = session_client.post(
            url, {"members": [{"member_id": str(other_member.id), "role": 5}]}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"] == GUEST_ROLE_DISABLED_ERROR
        assert not ProjectMember.objects.filter(project=project, member=other_member).exists()

    @pytest.mark.django_db
    def test_project_member_cannot_become_guest(self, session_client, workspace, project, other_member):
        project_member = ProjectMember.objects.create(project=project, member=other_member, role=15, is_active=True)
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/members/{project_member.id}/"

        response = session_client.patch(url, {"role": 5}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        project_member.refresh_from_db()
        assert project_member.role == 15

    @pytest.mark.django_db
    def test_public_api_invite_with_guest_role_is_refused(self, api_key_client, workspace):
        url = f"/api/v1/workspaces/{workspace.slug}/invitations/"

        response = api_key_client.post(url, {"email": "guest@infinity-africa.com", "role": 5}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not WorkspaceMemberInvite.objects.filter(workspace=workspace).exists()

    @pytest.mark.django_db
    def test_public_api_invite_defaults_to_member_role(self, api_key_client, workspace):
        url = f"/api/v1/workspaces/{workspace.slug}/invitations/"

        response = api_key_client.post(url, {"email": "new@infinity-africa.com"}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert WorkspaceMemberInvite.objects.get(workspace=workspace).role == 15


@pytest.mark.contract
class TestEstimatesDisabled:
    @pytest.mark.django_db
    def test_estimate_creation_is_refused(self, session_client, workspace, project):
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/estimates/"
        payload = {
            "estimate": {"name": "Points", "type": "points"},
            "estimate_points": [{"key": 1, "value": "1"}],
        }

        response = session_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"] == ESTIMATES_DISABLED_ERROR
        assert not Estimate.objects.filter(project=project).exists()

    @pytest.mark.django_db
    def test_project_cannot_be_linked_to_an_estimate(self, session_client, workspace, project):
        estimate = Estimate.objects.create(name="Points", project=project, workspace=workspace)
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/"

        response = session_client.patch(url, {"estimate": str(estimate.id)}, format="json")

        assert response.status_code == status.HTTP_200_OK
        project.refresh_from_db()
        assert project.estimate_id is None
