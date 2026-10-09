# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Project members as the MCP server manages them: membership ids, and members added back."""

import pytest
from rest_framework import status

from plane.db.models import Project, ProjectMember, User, WorkspaceMember


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="IAT", identifier="IAT", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(workspace=workspace, project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def colleague(workspace):
    user = User.objects.create(email="kofi@infinity-africa.com", username="kofi")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15, is_active=True)
    return user


def _url(workspace, project, suffix=""):
    return f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/{suffix}"


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectMemberManagement:
    def test_lite_listing_gives_the_membership_id(self, api_key_client, workspace, project, create_user):
        members = api_key_client.get(_url(workspace, project, "project-members-lite/")).json()["results"]

        membership = ProjectMember.objects.get(project=project, member=create_user)
        assert members[0]["id"] == str(create_user.id)
        assert members[0]["membership_id"] == str(membership.id)

    def test_a_removed_member_can_be_added_back(self, api_key_client, workspace, project, colleague):
        added = api_key_client.post(
            _url(workspace, project, "members/"), {"member": str(colleague.id), "role": 15}, format="json"
        )
        assert added.status_code == status.HTTP_201_CREATED
        membership = ProjectMember.objects.get(project=project, member=colleague)

        removed = api_key_client.delete(_url(workspace, project, f"members/{membership.id}/"))
        assert removed.status_code == status.HTTP_204_NO_CONTENT

        again = api_key_client.post(
            _url(workspace, project, "members/"), {"member": str(colleague.id), "role": 20}, format="json"
        )
        assert again.status_code == status.HTTP_201_CREATED
        membership.refresh_from_db()
        assert (membership.is_active, membership.role) == (True, 20)
        assert ProjectMember.objects.filter(project=project, member=colleague).count() == 1
