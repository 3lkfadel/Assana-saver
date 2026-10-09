# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tokens issued for Claude: creation, rate limit and "via Claude" in the task history."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.celery import app as celery_app
from plane.db.models import (
    APIToken,
    CustomField,
    Issue,
    IssueActivity,
    Project,
    ProjectCustomField,
    ProjectMember,
    State,
)

TOKENS_URL = "/api/users/api-tokens/"


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
def claude_client(db, create_user):
    token = APIToken.objects.create(user=create_user, label="Claude", client="claude", token="claude-token")
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=token.token)
    return client


@pytest.mark.contract
@pytest.mark.django_db
class TestClientTokenCreation:
    def test_claude_token_defaults_to_90_days_and_is_shown_once(self, session_client):
        response = session_client.post(TOKENS_URL, {"client": "claude"}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["client"] == "claude"
        assert body["label"] == "Claude"
        assert body["token"].startswith("plane_api_")
        token = APIToken.objects.get(pk=body["id"])
        assert abs(token.expired_at - (timezone.now() + timedelta(days=90))) < timedelta(minutes=1)

        listing = session_client.get(TOKENS_URL).json()
        assert listing[0]["client"] == "claude"
        assert "token" not in listing[0]

    def test_validity_can_be_chosen_or_unlimited(self, session_client):
        yearly = session_client.post(TOKENS_URL, {"client": "claude", "expires_in_days": 365}, format="json")
        unlimited = session_client.post(TOKENS_URL, {"client": "claude", "expires_in_days": None}, format="json")

        assert yearly.status_code == unlimited.status_code == status.HTTP_201_CREATED
        assert APIToken.objects.get(pk=unlimited.json()["id"]).expired_at is None

    @pytest.mark.parametrize("payload", [{"client": "chatgpt"}, {"client": "claude", "expires_in_days": 7}])
    def test_rejects_unknown_clients_and_validities(self, session_client, payload):
        response = session_client.post(TOKENS_URL, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not APIToken.objects.exists()

    def test_client_cannot_be_changed_afterwards(self, session_client, create_user):
        token = APIToken.objects.create(user=create_user, label="Script")

        session_client.patch(f"{TOKENS_URL}{token.id}/", {"client": "claude"}, format="json")

        token.refresh_from_db()
        assert token.client == ""


@pytest.mark.contract
@pytest.mark.django_db
class TestClientTokenUsage:
    def test_claude_tokens_have_the_client_rate_limit(self, claude_client, api_key_client, workspace):
        url = f"/api/v1/workspaces/{workspace.slug}/members/"

        assert claude_client.get(url)["X-RateLimit-Remaining"] == "299"
        assert api_key_client.get(url)["X-RateLimit-Remaining"] == "59"

    def test_changes_are_marked_via_claude(self, claude_client, workspace, project):
        field = CustomField.objects.create(workspace=workspace, name="Budget", field_type="number")
        ProjectCustomField.objects.create(project=project, workspace=workspace, custom_field=field)
        base = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/work-items/"

        created = claude_client.post(base, {"name": "Préparer le comité"}, format="json")
        assert created.status_code == status.HTTP_201_CREATED
        issue = Issue.issue_objects.get(pk=created.json()["id"])
        claude_client.put(f"{base}{issue.id}/custom-fields/{field.id}/", {"value": 1000}, format="json")

        activities = IssueActivity.objects.filter(issue=issue)
        assert activities.filter(field="custom_field").exists()
        assert set(activities.values_list("via", flat=True)) == {"claude"}

    def test_other_tokens_leave_via_empty(self, api_key_client, workspace, project):
        url = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/work-items/"

        created = api_key_client.post(url, {"name": "Tâche de script"}, format="json")

        assert set(IssueActivity.objects.filter(issue_id=created.json()["id"]).values_list("via", flat=True)) == {""}
