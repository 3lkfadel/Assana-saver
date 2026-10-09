# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Bulk creation and update of work items, with custom field values; closed cycle and module routes."""

import pytest
from rest_framework import status

from plane.celery import app as celery_app
from plane.db.models import (
    CustomField,
    Issue,
    IssueCustomFieldValue,
    Project,
    ProjectCustomField,
    ProjectMember,
    State,
)


@pytest.fixture(autouse=True)
def celery_eager():
    """Run the activity tasks in-process: there is no broker in the test stack."""
    original_always_eager = celery_app.conf.task_always_eager
    original_eager_propagates = celery_app.conf.task_eager_propagates
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = False
    yield
    celery_app.conf.task_always_eager = original_always_eager
    celery_app.conf.task_eager_propagates = original_eager_propagates


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="IAT", identifier="IAT", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(workspace=workspace, project=project, member=create_user, role=20, is_active=True)
    State.objects.create(project=project, workspace=workspace, name="À faire", group="unstarted", default=True)
    return project


@pytest.fixture
def budget(workspace, project):
    field = CustomField.objects.create(workspace=workspace, name="Budget", field_type="number")
    ProjectCustomField.objects.create(project=project, workspace=workspace, custom_field=field)
    return field


def _bulk_url(workspace, project):
    return f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/work-items/bulk/"


@pytest.mark.contract
@pytest.mark.django_db
class TestBulkCreate:
    def test_creates_items_in_order_with_custom_values(self, api_key_client, workspace, project, budget, create_user):
        payload = {
            "work_items": [
                {"name": "Rédiger le compte rendu", "custom_fields": {str(budget.id): 1200}},
                {"name": "Envoyer le devis", "priority": "high"},
            ]
        }

        response = api_key_client.post(_bulk_url(workspace, project), payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert [item["name"] for item in response.json()["work_items"]] == [
            "Rédiger le compte rendu",
            "Envoyer le devis",
        ]
        created = Issue.issue_objects.get(project=project, name="Rédiger le compte rendu")
        assert created.created_by_id == create_user.id
        assert IssueCustomFieldValue.objects.get(issue=created, custom_field=budget).value == 1200

    def test_is_all_or_nothing(self, api_key_client, workspace, project, budget):
        payload = {
            "work_items": [
                {"name": "Valide"},
                {"name": "Budget invalide", "custom_fields": {str(budget.id): "beaucoup"}},
                {"description_html": "<p>sans nom</p>"},
            ]
        }

        response = api_key_client.post(_bulk_url(workspace, project), payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert [error["index"] for error in response.json()["errors"]] == [1, 2]
        assert not Issue.issue_objects.filter(project=project).exists()

    def test_rejects_fields_outside_the_project(self, api_key_client, workspace, project):
        other = CustomField.objects.create(workspace=workspace, name="Hors projet", field_type="text")
        payload = {"work_items": [{"name": "Tâche", "custom_fields": {str(other.id): "x"}}]}

        response = api_key_client.post(_bulk_url(workspace, project), payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("work_items", [[], "tâche", [{"name": f"T{i}"} for i in range(101)]])
    def test_rejects_empty_malformed_or_oversized_batches(self, api_key_client, workspace, project, work_items):
        response = api_key_client.post(_bulk_url(workspace, project), {"work_items": work_items}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not Issue.issue_objects.filter(project=project).exists()


@pytest.mark.contract
@pytest.mark.django_db
class TestBulkUpdate:
    def _issue(self, project, name):
        return Issue.objects.create(
            project=project, workspace=project.workspace, name=name, state=State.objects.get(project=project)
        )

    def test_updates_fields_and_custom_values(self, api_key_client, workspace, project, budget):
        first, second = self._issue(project, "Lot 2 - étude"), self._issue(project, "Lot 2 - travaux")
        payload = {
            "work_items": [
                {"id": str(first.id), "priority": "urgent", "custom_fields": {str(budget.id): 500}},
                {"id": str(second.id), "custom_fields": {str(budget.id): 800}},
            ]
        }

        response = api_key_client.patch(_bulk_url(workspace, project), payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        first.refresh_from_db()
        assert first.priority == "urgent"
        assert {value.issue_id: value.value for value in IssueCustomFieldValue.objects.filter(custom_field=budget)} == {
            first.id: 500,
            second.id: 800,
        }

    def test_unknown_or_foreign_items_fail_the_batch(self, api_key_client, workspace, project, create_user):
        issue = self._issue(project, "Locale")
        other_project = Project.objects.create(
            name="Autre", identifier="AUT", workspace=workspace, created_by=create_user
        )
        State.objects.create(project=other_project, workspace=workspace, name="À faire", group="unstarted")
        foreign = self._issue(other_project, "Étrangère")
        payload = {
            "work_items": [
                {"id": str(issue.id), "name": "Renommée"},
                {"id": str(foreign.id), "name": "Piratée"},
                {"id": "pas-un-uuid", "name": "?"},
            ]
        }

        response = api_key_client.patch(_bulk_url(workspace, project), payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert [error["index"] for error in response.json()["errors"]] == [1, 2]
        issue.refresh_from_db()
        assert issue.name == "Locale"

    def test_rejects_missing_and_duplicate_ids(self, api_key_client, workspace, project):
        issue = self._issue(project, "Unique")
        url = _bulk_url(workspace, project)

        assert api_key_client.patch(url, {"work_items": [{"name": "x"}]}, format="json").status_code == 400
        duplicate = {"work_items": [{"id": str(issue.id)}, {"id": str(issue.id)}]}
        assert api_key_client.patch(url, duplicate, format="json").status_code == 400


@pytest.mark.contract
@pytest.mark.django_db
class TestClosedRoutes:
    @pytest.mark.parametrize("resource", ["cycles", "modules", "estimates"])
    def test_cycles_modules_and_estimates_are_not_exposed(self, api_key_client, workspace, project, resource):
        response = api_key_client.get(f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/{resource}/")

        assert response.status_code == status.HTTP_404_NOT_FOUND
