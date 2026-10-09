# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""AI assistant: access scope, read-only tools, deadline verdicts, endpoints and the tool-use loop."""

import json
from datetime import date, timedelta
from types import SimpleNamespace
from unittest import mock

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.app.views.assistant import agent
from plane.app.views.assistant.tools import (
    ToolInputError,
    build_scope,
    deadline_status,
    run_tool,
)
from plane.db.models import Issue, Project, ProjectMember, State, User, WorkspaceMember

TODAY = date(2026, 10, 7)


def _make_user(email: str) -> User:
    local_part = email.split("@")[0]
    user = User.objects.create(email=email, username=local_part, first_name=local_part, display_name=local_part)
    user.set_password("test-password")
    user.save()
    return user


def _make_project(workspace, owner, name: str, identifier: str) -> Project:
    project = Project.objects.create(name=name, identifier=identifier, workspace=workspace, created_by=owner)
    for sequence, (state_name, group) in enumerate(
        [("Prospect", "backlog"), ("En cours", "started"), ("Signé", "completed"), ("Abandonné", "cancelled")]
    ):
        State.objects.create(
            project=project, workspace=workspace, name=state_name, group=group, sequence=(sequence + 1) * 1000
        )
    return project


def _state(project: Project, group: str) -> State:
    return State.objects.get(project=project, group=group)


def _issue(project: Project, name: str, group: str, target_date=None, completed_on=None, assignee=None) -> Issue:
    issue = Issue.objects.create(
        project=project, workspace=project.workspace, name=name, state=_state(project, group), target_date=target_date
    )
    if assignee:
        issue.assignees.add(assignee, through_defaults={"project": project, "workspace": project.workspace})
    if completed_on:
        Issue.objects.filter(pk=issue.pk).update(
            completed_at=timezone.make_aware(timezone.datetime(completed_on.year, completed_on.month, completed_on.day))
        )
    return issue


@pytest.fixture
def projects(db, workspace, create_user):
    """Two projects; ``create_user`` (workspace admin) belongs to IAT only, as project admin."""
    iat = _make_project(workspace, create_user, "IAT — CONSULTING", "IAT")
    other = _make_project(workspace, create_user, "Secret", "SEC")
    ProjectMember.objects.create(workspace=workspace, project=iat, member=create_user, role=20, is_active=True)
    return SimpleNamespace(iat=iat, other=other)


@pytest.fixture
def frozen_today():
    with mock.patch("plane.app.views.assistant.tools._today", return_value=TODAY):
        yield TODAY


@pytest.mark.unit
class TestDeadlineStatus:
    def test_no_due_date(self):
        assert deadline_status(None, "started", None, TODAY) == {"status": "no_due_date"}

    def test_open_item_past_due_is_overdue(self):
        assert deadline_status(TODAY - timedelta(days=3), "started", None, TODAY) == {
            "status": "overdue",
            "days_late": 3,
        }

    def test_open_item_due_later_is_on_track(self):
        assert deadline_status(TODAY + timedelta(days=5), "backlog", None, TODAY) == {
            "status": "on_track",
            "days_remaining": 5,
        }

    def test_completed_after_due_date_is_late(self):
        completed_at = timezone.make_aware(timezone.datetime(2026, 10, 5, 12))
        result = deadline_status(date(2026, 10, 1), "completed", completed_at, TODAY)
        assert result["status"] == "completed_late"
        assert result["days_late"] == 4

    def test_completed_on_due_date_is_on_time(self):
        completed_at = timezone.make_aware(timezone.datetime(2026, 10, 1, 9))
        assert deadline_status(date(2026, 10, 1), "completed", completed_at, TODAY)["status"] == "completed_on_time"

    def test_cancelled_is_never_late(self):
        assert deadline_status(TODAY - timedelta(days=30), "cancelled", None, TODAY) == {"status": "cancelled"}


@pytest.mark.contract
@pytest.mark.django_db
class TestAssistantScope:
    def test_workspace_admin_sees_projects_they_belong_to(self, workspace, create_user, projects):
        scope = build_scope(create_user, workspace.slug)
        assert scope.project_ids == frozenset({str(projects.iat.id)})

    def test_project_admin_sees_only_administered_projects(self, workspace, projects):
        manager = _make_user("manager@plane.so")
        WorkspaceMember.objects.create(workspace=workspace, member=manager, role=15, is_active=True)
        ProjectMember.objects.create(workspace=workspace, project=projects.iat, member=manager, role=20)
        ProjectMember.objects.create(workspace=workspace, project=projects.other, member=manager, role=15)
        assert build_scope(manager, workspace.slug).project_ids == frozenset({str(projects.iat.id)})

    def test_plain_member_has_no_access(self, workspace, projects):
        member = _make_user("member@plane.so")
        WorkspaceMember.objects.create(workspace=workspace, member=member, role=15, is_active=True)
        ProjectMember.objects.create(workspace=workspace, project=projects.iat, member=member, role=15)
        assert build_scope(member, workspace.slug).is_empty


@pytest.mark.contract
@pytest.mark.django_db
class TestAssistantTools:
    def test_search_never_returns_out_of_scope_work_items(self, workspace, create_user, projects, frozen_today):
        _issue(projects.iat, "Migration Exchange OBF", "started")
        _issue(projects.other, "Migration secrète", "started")
        scope = build_scope(create_user, workspace.slug)

        result = json.loads(run_tool(scope, "search_work_items", {"query": "Migration"}))

        assert [item["name"] for item in result["work_items"]] == ["Migration Exchange OBF"]

    def test_out_of_scope_project_and_work_item_are_rejected(self, workspace, create_user, projects, frozen_today):
        secret = _issue(projects.other, "Migration secrète", "started")
        scope = build_scope(create_user, workspace.slug)

        with pytest.raises(ToolInputError):
            run_tool(scope, "project_progress", {"project": "SEC"})
        with pytest.raises(ToolInputError):
            run_tool(scope, "get_work_item", {"work_item": f"SEC-{secret.sequence_id}"})

    def test_deadline_report_counts_delays_per_assignee(self, workspace, create_user, projects, frozen_today):
        _issue(projects.iat, "Offre MDM", "started", target_date=TODAY - timedelta(days=10), assignee=create_user)
        _issue(projects.iat, "Audit Orange", "completed", target_date=date(2026, 9, 1), completed_on=date(2026, 9, 4))
        _issue(projects.iat, "Rendez-vous", "completed", target_date=date(2026, 9, 1), completed_on=date(2026, 8, 30))
        _issue(projects.iat, "Sans date", "started")
        scope = build_scope(create_user, workspace.slug)

        report = json.loads(run_tool(scope, "deadline_report", {"project": "IAT"}))

        assert report["overdue_count"] == 1
        assert report["overdue"][0]["deadline"] == {"status": "overdue", "days_late": 10}
        assert report["completed_late_count"] == 1
        assert report["completed_late"][0]["deadline"]["days_late"] == 3
        assert report["completed_on_time_count"] == 1
        assert report["by_assignee"][create_user.display_name]["overdue"] == 1

    def test_get_work_item_by_reference(self, workspace, create_user, projects, frozen_today):
        issue = _issue(projects.iat, "Offre MDM", "started", target_date=TODAY + timedelta(days=2))
        scope = build_scope(create_user, workspace.slug)

        result = json.loads(run_tool(scope, "get_work_item", {"work_item": f"IAT-{issue.sequence_id}"}))

        assert result["work_item"]["name"] == "Offre MDM"
        assert result["work_item"]["deadline"] == {"status": "on_track", "days_remaining": 2}

    def test_invalid_arguments_are_reported_to_the_model(self, workspace, create_user, projects):
        scope = build_scope(create_user, workspace.slug)
        with pytest.raises(ToolInputError):
            run_tool(scope, "search_work_items", {"overdue_only": "yes"})
        with pytest.raises(ToolInputError):
            run_tool(scope, "drop_table", {})


@pytest.mark.contract
@pytest.mark.django_db
class TestAssistantEndpoints:
    def _url(self, slug: str, suffix: str = "") -> str:
        return f"/api/workspaces/{slug}/assistant/{suffix}"

    def test_status_reports_configuration_and_access(self, session_client, workspace, projects):
        with mock.patch("plane.app.views.assistant.base.get_assistant_config", return_value=(None, "claude-opus-5-5")):
            response = session_client.get(self._url(workspace.slug))
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"is_configured": False, "is_allowed": True}

    def test_plain_member_is_forbidden(self, workspace, projects):
        member = _make_user("member@plane.so")
        WorkspaceMember.objects.create(workspace=workspace, member=member, role=15, is_active=True)
        client = APIClient()
        client.force_authenticate(user=member)

        response = client.post(
            self._url(workspace.slug, "chat/"), {"messages": [{"role": "user", "content": "Hi"}]}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_chat_requires_configuration(self, session_client, workspace, projects):
        with mock.patch("plane.app.views.assistant.base.get_assistant_config", return_value=(None, "claude-opus-5-5")):
            response = session_client.post(
                self._url(workspace.slug, "chat/"), {"messages": [{"role": "user", "content": "Hi"}]}, format="json"
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_chat_rejects_malformed_history(self, session_client, workspace, projects):
        with mock.patch("plane.app.views.assistant.base.get_assistant_config", return_value=("key", "model")):
            response = session_client.post(
                self._url(workspace.slug, "chat/"),
                {"messages": [{"role": "assistant", "content": "Only me"}]},
                format="json",
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_chat_streams_events_with_context(self, session_client, workspace, projects):
        issue = _issue(projects.iat, "Offre MDM", "started")
        captured = {}

        def fake_run_assistant(**kwargs):
            captured.update(kwargs)
            yield {"type": "text", "text": "Bonjour"}
            yield {"type": "done"}

        with (
            mock.patch("plane.app.views.assistant.base.get_assistant_config", return_value=("key", "model")),
            mock.patch("plane.app.views.assistant.base.run_assistant", side_effect=fake_run_assistant),
        ):
            response = session_client.post(
                self._url(workspace.slug, "chat/"),
                {
                    "messages": [{"role": "user", "content": "Où en est cette tâche ?"}],
                    "context": {"work_item_id": str(issue.id)},
                },
                format="json",
            )
            body = b"".join(response.streaming_content).decode()

        assert response["Content-Type"] == "text/event-stream"
        assert 'data: {"type": "text", "text": "Bonjour"}' in body
        assert f"IAT-{issue.sequence_id}" in captured["messages"][-1]["content"]
        assert captured["messages"][-1]["content"].endswith("Où en est cette tâche ?")


class _FakeStream:
    """Mimics the SDK stream context manager: iterates events, then returns the final message."""

    def __init__(self, events, final_message):
        self._events = events
        self._final_message = final_message

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def __iter__(self):
        return iter(self._events)

    def get_final_message(self):
        return self._final_message


def _fake_client(turns):
    calls = []

    def stream(**kwargs):
        # the SDK serializes the request at call time; snapshot the list the loop keeps appending to
        calls.append({**kwargs, "messages": list(kwargs["messages"])})
        return turns[len(calls) - 1]

    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(stream=stream)))
    return client, calls


@pytest.mark.unit
class TestAssistantLoop:
    def test_runs_tools_then_streams_the_answer(self):
        tool_use = SimpleNamespace(type="tool_use", id="toolu_1", name="list_projects", input={})
        turns = [
            _FakeStream([], SimpleNamespace(stop_reason="tool_use", content=[tool_use])),
            _FakeStream(
                [SimpleNamespace(type="text", text="2 projets.")],
                SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="2 projets.")]),
            ),
        ]
        client, calls = _fake_client(turns)

        with (
            mock.patch.object(agent.anthropic, "Anthropic", return_value=client),
            mock.patch.object(agent, "run_tool", return_value='{"projects": []}') as run_tool_mock,
        ):
            events = list(agent.run_assistant(api_key="k", model="m", scope=object(), messages=[]))

        assert [event["type"] for event in events] == ["status", "text", "done"]
        run_tool_mock.assert_called_once()
        assert calls[0]["fallbacks"] == "default"
        assert calls[0]["betas"] == [agent.FALLBACK_BETA]
        assert all(tool["eager_input_streaming"] for tool in calls[0]["tools"])
        second_turn_messages = calls[1]["messages"]
        assert second_turn_messages[-1]["content"][0] == {
            "type": "tool_result",
            "tool_use_id": "toolu_1",
            "content": '{"projects": []}',
        }

    def test_refusal_is_reported(self):
        client, _ = _fake_client([_FakeStream([], SimpleNamespace(stop_reason="refusal", content=[]))])
        with mock.patch.object(agent.anthropic, "Anthropic", return_value=client):
            events = list(agent.run_assistant(api_key="k", model="m", scope=object(), messages=[]))
        assert events == [{"type": "error", "code": "refusal"}, {"type": "done"}]

    def test_tool_input_errors_go_back_to_the_model(self):
        tool_use = SimpleNamespace(type="tool_use", id="toolu_1", name="get_work_item", input={})
        turns = [
            _FakeStream([], SimpleNamespace(stop_reason="tool_use", content=[tool_use])),
            _FakeStream([], SimpleNamespace(stop_reason="end_turn", content=[])),
        ]
        client, calls = _fake_client(turns)
        with (
            mock.patch.object(agent.anthropic, "Anthropic", return_value=client),
            mock.patch.object(agent, "run_tool", side_effect=ToolInputError("'work_item' is required")),
        ):
            list(agent.run_assistant(api_key="k", model="m", scope=object(), messages=[]))
        result = calls[1]["messages"][-1]["content"][0]
        assert result["is_error"] is True
        assert "work_item" in result["content"]
