"""Read tools against a simulated API."""

import httpx
from conftest import API, WS, page, query_item


async def test_whoami_gives_the_person_and_today(api, call):
    result = await call("whoami")

    assert result == {
        "user": {"id": "u-me", "name": "Awa", "email": "awa@infinity-africa.com"},
        "organisation": "infinity",
        "today": "2026-10-09",
    }
    assert api.calls.last.request.headers["X-Api-Key"] == "tok"


async def test_get_project_by_identifier_lists_what_tasks_need(api, call):
    result = await call("get_project", project="iat")

    assert result["name"] == "Infinity Africa Tech"
    assert result["url"] == "https://plan.test/infinity/projects/p-iat/issues/"
    assert [section["name"] for section in result["sections"]] == ["À faire", "Terminé"]
    assert [member["name"] for member in result["members"]] == ["Awa", "Kofi"]
    assert result["custom_fields"][1] == {
        "id": "cf-wave",
        "name": "Vague",
        "type": "single_select",
        "options": [{"id": "o-1", "name": "Vague 1"}, {"id": "o-2", "name": "Vague 2"}],
    }


async def test_unknown_project_names_the_available_ones(api, call_error):
    message = await call_error("get_project", project="RH")

    assert "No project 'RH'" in message
    assert "IAT (Infinity Africa Tech)" in message


async def test_search_tasks_translates_filters(api, call):
    route = api.get(f"{WS}/work-items/").respond(
        json=page([query_item(12, "Relancer le fournisseur", due="2026-10-06")])
    )

    result = await call(
        "search_tasks", project=["IAT"], assignee="Kofi", completed=False, section="à faire", order_by="-due_date"
    )

    params = route.calls.last.request.url.params
    assert params["project"] == "p-iat"
    assert params["assignee"] == "u-kofi"
    assert params["completed"] == "false"
    assert params["state"] == "s-todo"
    assert params["order_by"] == "-target_date"
    assert result["tasks"] == [
        {
            "identifier": "IAT-12",
            "name": "Relancer le fournisseur",
            "project": "Infinity Africa Tech",
            "section": "À faire",
            "completed": False,
            "assignees": ["Awa"],
            "due_date": "2026-10-06",
            "start_date": None,
            "priority": "none",
            "labels": [],
            "url": "https://plan.test/infinity/browse/IAT-12/",
        }
    ]


async def test_section_filter_needs_one_project(api, call_error):
    message = await call_error("search_tasks", section="À faire")

    assert "exactly one project" in message


async def test_my_tasks_groups_overdue_soon_and_undated(api, call):
    def respond(request: httpx.Request):
        if "due_before" in request.url.params:
            assert request.url.params["due_before"] == "2026-10-16"
            return httpx.Response(
                200,
                json=page([query_item(1, "En retard", due="2026-10-01"), query_item(2, "Bientôt", due="2026-10-12")]),
            )
        return httpx.Response(
            200, json=page([query_item(1, "En retard", due="2026-10-01"), query_item(3, "Sans date")])
        )

    api.get(f"{WS}/work-items/").mock(side_effect=respond)

    result = await call("my_tasks")

    assert [task["name"] for task in result["overdue"]] == ["En retard"]
    assert [task["name"] for task in result["due_soon"]] == ["Bientôt"]
    assert [task["name"] for task in result["no_due_date"]] == ["Sans date"]
    assert result["incomplete_list"] is False


async def test_get_task_reads_custom_fields_comments_and_subtasks(api, call):
    api.get(f"{WS}/work-items/IAT-12/").respond(
        json={
            "id": "t-12",
            "project": "p-iat",
            "sequence_id": 12,
            "name": "Offre MDM",
            "state": "s-todo",
            "assignees": [{"id": "u-kofi", "display_name": "Kofi"}],
            "labels": [{"id": "l-client", "name": "Client"}],
            "description_html": "<p>Préparer l'offre</p><ul><li>Prix</li><li>Délais</li></ul>",
            "target_date": "2026-10-20",
            "parent": None,
        }
    )
    api.get(f"{WS}/projects/p-iat/custom-field-values/").respond(
        json=[{"custom_field_id": "cf-budget", "value": 1500.5}, {"custom_field_id": "cf-wave", "value": "o-2"}]
    )
    subtasks = api.get(f"{WS}/work-items/").respond(json=page([query_item(13, "Chiffrer", parent="t-12")]))
    api.get(f"{WS}/projects/p-iat/work-items/t-12/comments/").respond(
        json=page(
            [
                {
                    "id": "c-1",
                    "actor": "u-me",
                    "created_at": "2026-10-08T10:00:00Z",
                    "comment_html": "<p>Vu avec le client</p>",
                }
            ]
        )
    )

    result = await call("get_task", task="iat-12")

    assert result["identifier"] == "IAT-12"
    assert result["url"] == "https://plan.test/infinity/browse/IAT-12/"
    assert result["section"] == "À faire"
    assert result["completed"] is False
    assert result["description"] == "Préparer l'offre\n\n- Prix\n- Délais"
    assert result["custom_fields"] == {"Budget": 1500.5, "Vague": "Vague 2"}
    assert [task["identifier"] for task in result["subtasks"]] == ["IAT-13"]
    assert subtasks.calls.last.request.url.params["parent"] == "t-12"
    assert result["comments"] == [
        {"id": "c-1", "author": "Awa", "date": "2026-10-08T10:00:00Z", "text": "Vu avec le client"}
    ]


async def test_bad_task_identifier(api, call_error):
    assert "use the form IAT-12" in await call_error("get_task", task="offre MDM")


async def test_project_overview_counts(api, call):
    api.get(f"{WS}/work-items/").respond(
        json=page(
            [
                query_item(1, "En retard", due="2026-10-01"),
                query_item(2, "Cette semaine", due="2026-10-14", assignees=("Kofi",)),
                query_item(3, "Plus tard", due="2026-11-30", assignees=()),
                query_item(4, "Fait", due="2026-10-02", done=True),
            ]
        )
    )

    result = await call("project_overview", project="IAT")

    assert (result["open"], result["completed"]) == (3, 1)
    assert [task["name"] for task in result["overdue"]] == ["En retard"]
    assert [task["name"] for task in result["due_this_week"]] == ["Cette semaine"]
    assert result["open_by_person"] == {"Awa": 1, "Kofi": 1, "(unassigned)": 1}
    assert result["open_by_section"] == {"À faire": 3}


async def test_api_errors_are_explained(api, call_error):
    api.get(f"{API}/users/me/").respond(status_code=401, json={"detail": "Invalid token"})

    assert "Connect Claude" in await call_error("whoami")
