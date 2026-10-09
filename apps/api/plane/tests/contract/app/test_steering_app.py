# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Group referential of the steering space: branches, entities, categories, profiles, project entity."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    Branch,
    Entity,
    Project,
    ProjectMember,
    ProjectSteering,
    SteeringCategory,
    SteeringProfile,
    User,
    Workspace,
    WorkspaceMember,
)


def _url(slug, suffix=""):
    return f"/api/workspaces/{slug}/steering/{suffix}"


@pytest.fixture
def member(workspace):
    user = User.objects.create(email="membre@example.com", username="membre")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15, is_active=True)
    return user


@pytest.fixture
def member_client(member):
    client = APIClient()
    client.force_authenticate(user=member)
    return client


@pytest.fixture
def branch(workspace):
    return Branch.objects.create(workspace=workspace, name="Immobilier", sort_order=1000)


@pytest.fixture
def entity(workspace, branch):
    return Entity.objects.create(workspace=workspace, branch=branch, name="SCI Infinity", sort_order=1000)


@pytest.fixture
def project(workspace, create_user):
    project = Project.objects.create(name="Tour IAT", identifier="TOUR", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(workspace=workspace, project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.mark.contract
@pytest.mark.django_db
class TestReferential:
    def test_bootstrap_seeds_the_specification_once(self, session_client, workspace):
        response = session_client.post(_url(workspace.slug, "bootstrap/"))
        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert len(body["branches"]) == 8
        assert len(body["entities"]) == 21
        assert [category["name"] for category in body["categories"]] == [
            "Agréments",
            "Gouvernance",
            "Partenariats",
            "Développement",
        ]
        fonctions_groupe = Branch.objects.get(workspace=workspace, name="Fonctions Groupe")
        assert fonctions_groupe.entities.count() == 7
        assert session_client.post(_url(workspace.slug, "bootstrap/")).status_code == status.HTTP_400_BAD_REQUEST

    def test_members_read_but_do_not_change_the_referential(self, member_client, workspace, entity):
        body = member_client.get(_url(workspace.slug)).json()
        assert body["can_administer"] is False
        assert body["entities"] == [
            {"id": str(entity.id), "name": "SCI Infinity", "branch_id": str(entity.branch_id), "sort_order": 1000}
        ]
        assert member_client.post(_url(workspace.slug, "branches/"), {"name": "Agro"}, format="json").status_code == (
            status.HTTP_403_FORBIDDEN
        )
        assert member_client.post(_url(workspace.slug, "bootstrap/")).status_code == status.HTTP_403_FORBIDDEN

    def test_the_cabinet_administers_the_referential(self, member_client, member, workspace):
        SteeringProfile.objects.create(workspace=workspace, member=member, role="cabinet")
        assert member_client.get(_url(workspace.slug)).json()["can_administer"] is True
        response = member_client.post(_url(workspace.slug, "branches/"), {"name": "Agro"}, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_outsiders_cannot_read(self, workspace):
        outsider = User.objects.create(email="outsider@example.com", username="outsider")
        client = APIClient()
        client.force_authenticate(user=outsider)
        assert client.get(_url(workspace.slug)).status_code == status.HTTP_403_FORBIDDEN

    def test_branches_and_entities(self, session_client, workspace, branch, entity):
        branches_url = _url(workspace.slug, "branches/")
        assert session_client.post(branches_url, {"name": "Immobilier"}, format="json").status_code == 400
        assert session_client.post(branches_url, {"name": "  "}, format="json").status_code == 400
        technologie = session_client.post(branches_url, {"name": "Technologie"}, format="json").json()
        assert technologie["sort_order"] == 2000

        renamed = session_client.patch(_url(workspace.slug, f"branches/{branch.id}/"), {"name": "Immobilier & BTP"})
        assert renamed.json()["name"] == "Immobilier & BTP"

        # A branch holding entities cannot be deleted; moving its entity away frees it.
        assert session_client.delete(_url(workspace.slug, f"branches/{branch.id}/")).status_code == 400
        moved = session_client.patch(
            _url(workspace.slug, f"entities/{entity.id}/"), {"branch_id": technologie["id"]}, format="json"
        )
        assert moved.json()["branch_id"] == technologie["id"]
        assert session_client.delete(_url(workspace.slug, f"branches/{branch.id}/")).status_code == 204
        assert not Branch.objects.filter(pk=branch.id).exists()

    def test_entity_needs_a_branch_of_the_workspace(self, session_client, workspace, create_user):
        other = Workspace.objects.create(name="Autre", owner=create_user, slug="autre")
        foreign_branch = Branch.objects.create(workspace=other, name="Ailleurs")
        payload = {"name": "Infinity Sports SAS", "branch_id": str(foreign_branch.id)}
        assert session_client.post(_url(workspace.slug, "entities/"), payload, format="json").status_code == 400

    def test_entity_carrying_projects_is_kept(self, session_client, workspace, entity, project):
        ProjectSteering.objects.create(project=project, workspace=workspace, entity=entity)
        assert session_client.delete(_url(workspace.slug, f"entities/{entity.id}/")).status_code == 400
        ProjectSteering.objects.filter(project=project).delete(soft=False)
        assert session_client.delete(_url(workspace.slug, f"entities/{entity.id}/")).status_code == 204

    def test_categories(self, session_client, workspace):
        created = session_client.post(_url(workspace.slug, "categories/"), {"name": "Agréments"}, format="json")
        assert created.status_code == 201
        category_url = _url(workspace.slug, f"categories/{created.json()['id']}/")
        assert session_client.patch(category_url, {"name": "Licences"}).json()["name"] == "Licences"
        assert session_client.delete(category_url).status_code == 204
        assert not SteeringCategory.objects.filter(workspace=workspace).exists()


@pytest.mark.contract
@pytest.mark.django_db
class TestProfiles:
    def test_profiles_need_their_scope(self, session_client, workspace, member, branch, entity):
        profiles_url = _url(workspace.slug, "profiles/")
        member_id = str(member.id)
        assert session_client.post(profiles_url, {"member_id": member_id, "role": "pope"}).status_code == 400
        assert session_client.post(profiles_url, {"member_id": member_id, "role": "branch_director"}).status_code == 400
        director = session_client.post(
            profiles_url, {"member_id": member_id, "role": "branch_director", "branch_id": str(branch.id)}
        )
        assert director.status_code == 201
        assert director.json()["branch_id"] == str(branch.id)
        manager = session_client.post(
            profiles_url, {"member_id": member_id, "role": "entity_manager", "entity_id": str(entity.id)}
        )
        assert manager.json()["entity_id"] == str(entity.id)
        ceo = {"member_id": member_id, "role": "ceo"}
        assert session_client.post(profiles_url, ceo).status_code == 201
        assert session_client.post(profiles_url, ceo).status_code == 400
        assert len(session_client.get(profiles_url).json()) == 3

    def test_profiles_are_for_workspace_members(self, session_client, workspace):
        outsider = User.objects.create(email="outsider@example.com", username="outsider")
        response = session_client.post(
            _url(workspace.slug, "profiles/"), {"member_id": str(outsider.id), "role": "ceo"}
        )
        assert response.status_code == 400

    def test_my_profiles_and_removal(self, session_client, member_client, workspace, member, entity):
        profile = SteeringProfile.objects.create(
            workspace=workspace, member=member, role="entity_manager", entity=entity
        )
        assert member_client.get(_url(workspace.slug)).json()["my_profiles"] == [
            {
                "id": str(profile.id),
                "member_id": str(member.id),
                "role": "entity_manager",
                "branch_id": None,
                "entity_id": str(entity.id),
            }
        ]
        assert member_client.get(_url(workspace.slug, "profiles/")).status_code == 403
        assert session_client.delete(_url(workspace.slug, f"profiles/{profile.id}/")).status_code == 204
        assert member_client.get(_url(workspace.slug)).json()["my_profiles"] == []


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectEntity:
    def _url(self, workspace, project):
        return f"/api/workspaces/{workspace.slug}/projects/{project.id}/steering/"

    def test_project_admin_sets_the_carrying_entity(self, session_client, workspace, project, entity, branch):
        url = self._url(workspace, project)
        assert session_client.get(url).json() == {"entity_id": None}
        assert session_client.put(url, {"entity_id": str(entity.id)}, format="json").status_code == 200
        other = Entity.objects.create(workspace=workspace, branch=branch, name="Infinity Africa Properties")
        session_client.put(url, {"entity_id": str(other.id)}, format="json")
        assert session_client.get(url).json() == {"entity_id": str(other.id)}
        assert ProjectSteering.objects.filter(project=project).count() == 1
        assert session_client.put(url, {"entity_id": None}, format="json").status_code == 400

    def test_project_members_cannot_change_it(self, member_client, member, workspace, project, entity):
        ProjectMember.objects.create(workspace=workspace, project=project, member=member, role=15, is_active=True)
        url = self._url(workspace, project)
        assert member_client.get(url).status_code == 200
        assert member_client.put(url, {"entity_id": str(entity.id)}, format="json").status_code == 403
        SteeringProfile.objects.create(workspace=workspace, member=member, role="cabinet")
        assert member_client.put(url, {"entity_id": str(entity.id)}, format="json").status_code == 200

    def test_project_of_another_workspace(self, session_client, workspace, entity, create_user):
        other = Workspace.objects.create(name="Autre", owner=create_user, slug="autre")
        foreign = Project.objects.create(name="Ailleurs", identifier="AIL", workspace=other, created_by=create_user)
        url = f"/api/workspaces/{workspace.slug}/projects/{foreign.id}/steering/"
        assert session_client.put(url, {"entity_id": str(entity.id)}, format="json").status_code == 404
