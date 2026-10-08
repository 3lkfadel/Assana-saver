# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Custom fields: organisation library, project attachment, values, history."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    CustomField,
    CustomFieldType,
    Issue,
    IssueActivity,
    IssueCustomFieldValue,
    Project,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
)
from plane.utils.custom_field import CustomFieldValueError, clean_custom_field_value


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
    return f"/api/workspaces/{slug}/{suffix}"


def _create_field(client, slug, **payload):
    return client.post(_url(slug, "custom-fields/"), payload, format="json")


@pytest.mark.unit
@pytest.mark.django_db
class TestCleanValue:
    def _field(self, workspace, field_type, **kwargs):
        return CustomField.objects.create(workspace=workspace, name=field_type, field_type=field_type, **kwargs)

    def test_number_is_rounded_to_precision_and_accepts_commas(self, workspace):
        field = self._field(workspace, CustomFieldType.NUMBER, number_precision=2)
        assert clean_custom_field_value(field, "95,456") == 95.46
        with pytest.raises(CustomFieldValueError):
            clean_custom_field_value(field, "abc")

    def test_date_and_text(self, workspace):
        date_field = self._field(workspace, CustomFieldType.DATE)
        assert clean_custom_field_value(date_field, "2026-10-07") == "2026-10-07"
        with pytest.raises(CustomFieldValueError):
            clean_custom_field_value(date_field, "07/10/2026")
        assert clean_custom_field_value(self._field(workspace, CustomFieldType.TEXT), "  Oui ") == "Oui"

    def test_empty_values_clear_the_field(self, workspace):
        field = self._field(workspace, CustomFieldType.TEXT)
        assert clean_custom_field_value(field, "") is None
        assert clean_custom_field_value(field, None) is None

    def test_people_must_be_organisation_members(self, workspace, create_user):
        field = self._field(workspace, CustomFieldType.PEOPLE)
        assert clean_custom_field_value(field, [str(create_user.id)]) == [str(create_user.id)]
        outsider = User.objects.create(email="outsider@example.com", username="outsider")
        with pytest.raises(CustomFieldValueError):
            clean_custom_field_value(field, [str(outsider.id)])


@pytest.mark.contract
@pytest.mark.django_db
class TestCustomFieldLibrary:
    def test_create_list_field_with_options(self, session_client, workspace):
        response = _create_field(
            session_client,
            workspace.slug,
            name="Vague",
            field_type="single_select",
            options=[{"name": "Vague 1 (2026)", "color": "#8b5cf6"}, {"name": "Vague 2 (2027)"}],
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert [option["name"] for option in response.json()["options"]] == ["Vague 1 (2026)", "Vague 2 (2027)"]

        listing = session_client.get(_url(workspace.slug, "custom-fields/"))
        assert [field["name"] for field in listing.json()] == ["Vague"]

    def test_rejects_duplicates_and_invalid_definitions(self, session_client, workspace):
        assert _create_field(session_client, workspace.slug, name="Budget", field_type="number").status_code == 201
        assert _create_field(session_client, workspace.slug, name="Budget", field_type="number").status_code == 400
        assert _create_field(session_client, workspace.slug, name="X", field_type="formula").status_code == 400
        assert (
            _create_field(session_client, workspace.slug, name="Liste", field_type="single_select").status_code == 400
        )
        duplicate_options = [{"name": "Oui"}, {"name": "oui"}]
        response = _create_field(
            session_client, workspace.slug, name="Interne", field_type="single_select", options=duplicate_options
        )
        assert response.status_code == 400

    def test_only_admins_delete_fields(self, workspace):
        member = User.objects.create(email="member@plane.so", username="member")
        WorkspaceMember.objects.create(workspace=workspace, member=member, role=15, is_active=True)
        field = CustomField.objects.create(workspace=workspace, name="Budget", field_type="number")
        client = APIClient()
        client.force_authenticate(user=member)

        response = client.delete(_url(workspace.slug, f"custom-fields/{field.id}/"))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert CustomField.objects.filter(pk=field.pk).exists()


@pytest.mark.contract
@pytest.mark.django_db
class TestCustomFieldValues:
    def _setup_field(self, client, workspace, project, **payload):
        field = _create_field(client, workspace.slug, **payload).json()
        attach = client.post(
            _url(workspace.slug, f"projects/{project.id}/custom-fields/"),
            {"custom_field_id": field["id"]},
            format="json",
        )
        assert attach.status_code == status.HTTP_201_CREATED
        return field

    def _value_url(self, workspace, project, issue, field):
        return _url(workspace.slug, f"projects/{project.id}/issues/{issue.id}/custom-fields/{field['id']}/")

    def test_set_change_and_clear_a_value_with_history(self, session_client, workspace, project, issue):
        field = self._setup_field(
            session_client,
            workspace,
            project,
            name="Interne",
            field_type="single_select",
            options=[{"name": "Oui"}, {"name": "Non"}],
        )
        oui, non = (option["id"] for option in field["options"])
        url = self._value_url(workspace, project, issue, field)

        assert session_client.put(url, {"value": oui}, format="json").json()["value"] == oui
        assert session_client.put(url, {"value": non}, format="json").status_code == status.HTTP_200_OK
        assert session_client.put(url, {"value": None}, format="json").json()["value"] is None

        history = IssueActivity.objects.filter(issue=issue, field="custom_field").order_by("created_at")
        assert [(entry.old_value, entry.new_value) for entry in history] == [("", "Oui"), ("Oui", "Non"), ("Non", "")]
        assert history.first().comment == "Interne"

    def test_rejects_invalid_values_and_detached_fields(self, session_client, workspace, project, issue):
        field = self._setup_field(session_client, workspace, project, name="Budget", field_type="number")
        url = self._value_url(workspace, project, issue, field)
        assert session_client.put(url, {"value": "beaucoup"}, format="json").status_code == 400
        assert session_client.put(url, {"value": "95,4"}, format="json").json()["value"] == 95
        assert IssueActivity.objects.filter(issue=issue, field="custom_field").get().new_value == "95"

        session_client.delete(_url(workspace.slug, f"projects/{project.id}/custom-fields/{field['id']}/"))
        assert session_client.put(url, {"value": 10}, format="json").status_code == 404

    def test_project_values_listing(self, session_client, workspace, project, issue):
        field = self._setup_field(session_client, workspace, project, name="Budget", field_type="number")
        session_client.put(self._value_url(workspace, project, issue, field), {"value": 95}, format="json")

        response = session_client.get(_url(workspace.slug, f"projects/{project.id}/custom-field-values/"))

        assert response.json() == [
            {
                "issue_id": str(issue.id),
                "custom_field_id": field["id"],
                "value": 95,
                "updated_at": response.json()[0]["updated_at"],
            }
        ]

    def test_removing_an_option_cleans_values(self, session_client, workspace, project, issue):
        field = self._setup_field(
            session_client,
            workspace,
            project,
            name="Tags",
            field_type="multi_select",
            options=[{"name": "IAT"}, {"name": "Interne"}],
        )
        iat, interne = (option["id"] for option in field["options"])
        session_client.put(self._value_url(workspace, project, issue, field), {"value": [iat, interne]}, format="json")

        response = session_client.patch(
            _url(workspace.slug, f"custom-fields/{field['id']}/"),
            {"options": [{"id": iat, "name": "IAT"}]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert IssueCustomFieldValue.objects.get(issue=issue).value == [iat]
