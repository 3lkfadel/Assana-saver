# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Work items across the caller's projects, with filters."""

from datetime import date, timedelta

import pytest
from rest_framework import status

from plane.db.models import (
    Issue,
    IssueAssignee,
    IssueLabel,
    Label,
    Project,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
)

TODAY = date(2026, 10, 9)


def _project(workspace, user, identifier, member=True):
    project = Project.objects.create(name=identifier, identifier=identifier, workspace=workspace, created_by=user)
    if member:
        ProjectMember.objects.create(workspace=workspace, project=project, member=user, role=20, is_active=True)
    State.objects.create(project=project, workspace=workspace, name="À faire", group="unstarted", default=True)
    State.objects.create(project=project, workspace=workspace, name="Fait", group="completed")
    return project


def _issue(project, name, done=False, due=None, assignee=None):
    state = State.objects.get(project=project, group="completed" if done else "unstarted")
    issue = Issue.objects.create(project=project, workspace=project.workspace, name=name, state=state, target_date=due)
    if assignee:
        IssueAssignee.objects.create(issue=issue, assignee=assignee, project=project, workspace=project.workspace)
    return issue


@pytest.fixture
def setup(db, workspace, create_user):
    colleague = User.objects.create(email="collegue@infinity-africa.com", username="collegue")
    WorkspaceMember.objects.create(workspace=workspace, member=colleague, role=15, is_active=True)
    iat, rh = _project(workspace, create_user, "IAT"), _project(workspace, create_user, "RH")
    hidden = _project(workspace, create_user, "SECRET", member=False)
    issues = {
        "late": _issue(iat, "Relancer le fournisseur", due=TODAY - timedelta(days=3), assignee=create_user),
        "week": _issue(rh, "Préparer le comité", due=TODAY + timedelta(days=2), assignee=create_user),
        "done": _issue(iat, "Signer le contrat", done=True, due=TODAY - timedelta(days=1), assignee=create_user),
        "other": _issue(iat, "Mettre à jour le budget", due=TODAY + timedelta(days=1), assignee=colleague),
        "nobody": _issue(rh, "Classer les archives"),
        "hidden": _issue(hidden, "Dossier confidentiel", assignee=create_user),
    }
    return {"iat": iat, "rh": rh, "colleague": colleague, "issues": issues}


def _names(response):
    return [item["name"] for item in response.json()["results"]]


URL = "/api/v1/workspaces/test-workspace/work-items/"


@pytest.mark.contract
@pytest.mark.django_db
class TestWorkItemQuery:
    def test_lists_only_the_callers_projects_ordered_by_due_date(self, api_key_client, setup):
        response = api_key_client.get(URL)

        assert response.status_code == status.HTTP_200_OK
        names = _names(response)
        assert "Dossier confidentiel" not in names
        assert names[:4] == [
            "Relancer le fournisseur",
            "Signer le contrat",
            "Mettre à jour le budget",
            "Préparer le comité",
        ]
        assert names[-1] == "Classer les archives"

    def test_my_open_tasks_due_this_week(self, api_key_client, setup):
        response = api_key_client.get(
            URL, {"assignee": "me", "completed": "false", "due_before": (TODAY + timedelta(days=7)).isoformat()}
        )

        assert _names(response) == ["Relancer le fournisseur", "Préparer le comité"]

    def test_overdue_tasks_of_a_project(self, api_key_client, setup):
        response = api_key_client.get(
            URL,
            {
                "project": str(setup["iat"].id),
                "completed": "false",
                "due_before": (TODAY - timedelta(days=1)).isoformat(),
            },
        )

        assert _names(response) == ["Relancer le fournisseur"]

    def test_assignee_filters(self, api_key_client, setup):
        assert _names(api_key_client.get(URL, {"assignee": "none"})) == ["Classer les archives"]
        assert _names(api_key_client.get(URL, {"assignee": str(setup["colleague"].id)})) == ["Mettre à jour le budget"]

    def test_label_and_search_filters(self, api_key_client, setup, workspace):
        label = Label.objects.create(name="Urgent client", project=setup["iat"], workspace=workspace)
        issue = setup["issues"]["other"]
        IssueLabel.objects.create(issue=issue, label=label, project=setup["iat"], workspace=workspace)

        assert _names(api_key_client.get(URL, {"label": str(label.id)})) == ["Mettre à jour le budget"]
        assert _names(api_key_client.get(URL, {"search": "comité"})) == ["Préparer le comité"]

    def test_results_are_compact_and_readable(self, api_key_client, setup, create_user):
        item = api_key_client.get(URL, {"search": "fournisseur"}).json()["results"][0]

        assert item["identifier"].startswith("IAT-")
        assert item["project"]["identifier"] == "IAT"
        assert item["state"]["name"] == "À faire"
        assert item["completed"] is False
        assert item["assignees"] == [{"id": str(create_user.id), "display_name": create_user.display_name}]

    @pytest.mark.parametrize(
        "params",
        [{"assignee": "quelqu'un"}, {"completed": "oui"}, {"due_before": "09/10/2026"}, {"priority": "critique"}],
    )
    def test_rejects_invalid_filters(self, api_key_client, setup, params):
        assert api_key_client.get(URL, params).status_code == status.HTTP_400_BAD_REQUEST
