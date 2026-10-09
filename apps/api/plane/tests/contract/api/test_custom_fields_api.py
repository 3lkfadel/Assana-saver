# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Custom fields in the public API (API key): library, project fields and task values."""

import pytest
from rest_framework import status

from plane.db.models import (
    CustomField,
    Issue,
    IssueActivity,
    IssueCustomFieldValue,
    Project,
    ProjectCustomField,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
)
from plane.db.models.api import APIToken


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="IAT", identifier="IAT", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(workspace=workspace, project=project, member=create_user, role=20, is_active=True)
    State.objects.create(project=project, workspace=workspace, name="En cours", group="started", default=True)
    return project


@pytest.fixture
def issue(project):
    return Issue.objects.create(
        project=project, workspace=project.workspace, name="Offre MDM", state=State.objects.get(project=project)
    )


def _url(slug, suffix=""):
    return f"/api/v1/workspaces/{slug}/{suffix}"


def _create_field(client, slug, **payload):
    return client.post(_url(slug, "custom-fields/"), payload, format="json")


def _attach(client, workspace, project, field_id):
    return client.post(
        _url(workspace.slug, f"projects/{project.id}/custom-fields/"), {"custom_field_id": field_id}, format="json"
    )


@pytest.mark.contract
@pytest.mark.django_db
class TestCustomFieldLibraryAPI:
    def test_create_list_retrieve_and_update(self, api_key_client, workspace):
        response = _create_field(
            api_key_client,
            workspace.slug,
            name="Vague",
            field_type="single_select",
            options=[{"name": "Vague 1"}, {"name": "Vague 2"}],
        )
        assert response.status_code == status.HTTP_201_CREATED
        field = response.json()
        assert [option["name"] for option in field["options"]] == ["Vague 1", "Vague 2"]

        listing = api_key_client.get(_url(workspace.slug, "custom-fields/"))
        assert [item["name"] for item in listing.json()] == ["Vague"]
        assert api_key_client.get(_url(workspace.slug, f"custom-fields/{field['id']}/")).status_code == 200

        kept = field["options"][1]
        updated = api_key_client.patch(
            _url(workspace.slug, f"custom-fields/{field['id']}/"),
            {"name": "Vague de déploiement", "options": [{"id": kept["id"], "name": "Vague 2"}, {"name": "Vague 3"}]},
            format="json",
        )
        assert updated.status_code == status.HTTP_200_OK
        assert updated.json()["name"] == "Vague de déploiement"
        assert [option["name"] for option in updated.json()["options"]] == ["Vague 2", "Vague 3"]

    def test_rejects_invalid_definitions(self, api_key_client, workspace):
        assert _create_field(api_key_client, workspace.slug, name="Budget", field_type="number").status_code == 201
        assert _create_field(api_key_client, workspace.slug, name="Budget", field_type="number").status_code == 400
        assert _create_field(api_key_client, workspace.slug, name="X", field_type="formula").status_code == 400
        assert _create_field(api_key_client, workspace.slug, name="L", field_type="single_select").status_code == 400

    def test_fields_cannot_be_deleted_through_the_api(self, api_key_client, workspace):
        field = CustomField.objects.create(workspace=workspace, name="Budget", field_type="number")

        response = api_key_client.delete(_url(workspace.slug, f"custom-fields/{field.id}/"))

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert CustomField.objects.filter(pk=field.pk).exists()

    def test_requires_organisation_membership(self, api_client, workspace):
        outsider = User.objects.create(email="outsider@example.com", username="outsider")
        token = APIToken.objects.create(user=outsider, label="Outsider", token="outsider-token")
        api_client.credentials(HTTP_X_API_KEY=token.token)

        assert api_client.get(_url(workspace.slug, "custom-fields/")).status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectCustomFieldsAPI:
    def test_attach_list_and_detach(self, api_key_client, workspace, project):
        field = _create_field(api_key_client, workspace.slug, name="Budget", field_type="number").json()

        assert _attach(api_key_client, workspace, project, field["id"]).status_code == status.HTTP_201_CREATED
        assert _attach(api_key_client, workspace, project, field["id"]).status_code == status.HTTP_400_BAD_REQUEST

        listing = api_key_client.get(_url(workspace.slug, f"projects/{project.id}/custom-fields/"))
        assert [item["custom_field"]["name"] for item in listing.json()] == ["Budget"]

        detach = api_key_client.delete(_url(workspace.slug, f"projects/{project.id}/custom-fields/{field['id']}/"))
        assert detach.status_code == status.HTTP_204_NO_CONTENT
        assert not ProjectCustomField.objects.filter(project=project).exists()

    def test_unknown_field_is_404(self, api_key_client, workspace, project):
        response = _attach(api_key_client, workspace, project, "00000000-0000-0000-0000-000000000000")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_project_guests_and_non_members_are_refused(self, api_client, workspace, project):
        member = User.objects.create(email="member@plane.so", username="member")
        WorkspaceMember.objects.create(workspace=workspace, member=member, role=15, is_active=True)
        token = APIToken.objects.create(user=member, label="Member", token="member-token")
        api_client.credentials(HTTP_X_API_KEY=token.token)

        response = api_client.get(_url(workspace.slug, f"projects/{project.id}/custom-fields/"))

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.contract
@pytest.mark.django_db
class TestCustomFieldValuesAPI:
    def _value_url(self, workspace, project, issue, field_id):
        return _url(workspace.slug, f"projects/{project.id}/work-items/{issue.id}/custom-fields/{field_id}/")

    def test_set_list_and_clear_a_value_with_history(self, api_key_client, workspace, project, issue):
        field = _create_field(
            api_key_client, workspace.slug, name="Budget", field_type="number", number_precision=2
        ).json()
        _attach(api_key_client, workspace, project, field["id"])
        url = self._value_url(workspace, project, issue, field["id"])

        response = api_key_client.put(url, {"value": "1500,5"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["value"] == 1500.5

        values = api_key_client.get(
            _url(workspace.slug, f"projects/{project.id}/custom-field-values/"), {"work_item_id": str(issue.id)}
        )
        assert [item["custom_field_id"] for item in values.json()] == [field["id"]]

        cleared = api_key_client.put(url, {"value": None}, format="json")
        assert cleared.status_code == status.HTTP_200_OK
        assert cleared.json()["value"] is None
        assert not IssueCustomFieldValue.objects.filter(issue=issue).exists()
        assert IssueActivity.objects.filter(issue=issue, field="custom_field").count() == 2

    def test_rejects_invalid_values_and_detached_fields(self, api_key_client, workspace, project, issue):
        field = _create_field(api_key_client, workspace.slug, name="Échéance", field_type="date").json()
        url = self._value_url(workspace, project, issue, field["id"])

        assert api_key_client.put(url, {"value": "2026-10-31"}, format="json").status_code == 404

        _attach(api_key_client, workspace, project, field["id"])
        assert api_key_client.put(url, {"value": "31/10/2026"}, format="json").status_code == 400
        assert api_key_client.put(url, {}, format="json").status_code == 400
