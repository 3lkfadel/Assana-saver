"""Find projects, tasks, sections, labels and people from what Claude knows: identifiers and names."""

import re
import uuid

from .api import InfinityAPI, InfinityAPIError

TASK_IDENTIFIER = re.compile(r"^\s*([A-Za-z0-9]+)-(\d+)\s*$")


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def _matches(value: str, *candidates: str | None) -> bool:
    wanted = value.strip().casefold()
    return any(candidate and candidate.strip().casefold() == wanted for candidate in candidates)


async def list_projects(api: InfinityAPI) -> list[dict]:
    projects, _ = await api.all_pages("projects/")
    return [project for project in projects if not project.get("archived_at")]


async def find_project(api: InfinityAPI, reference: str) -> dict:
    """A project by id, identifier (e.g. IAT) or exact name."""
    projects = await list_projects(api)
    for project in projects:
        if project["id"] == reference or _matches(reference, project.get("identifier"), project.get("name")):
            return project
    known = ", ".join(f"{project['identifier']} ({project['name']})" for project in projects) or "none"
    raise InfinityAPIError(f"No project '{reference}'. Projects you can access: {known}.")


async def find_task(api: InfinityAPI, reference: str) -> dict:
    """A task by identifier, e.g. IAT-12."""
    match = TASK_IDENTIFIER.match(reference)
    if not match:
        raise InfinityAPIError(f"'{reference}' is not a task identifier; use the form IAT-12.")
    identifier = f"{match.group(1).upper()}-{match.group(2)}"
    return await api.get(f"work-items/{identifier}/", expand="assignees,labels")


async def project_states(api: InfinityAPI, project_id: str) -> list[dict]:
    states, _ = await api.all_pages(f"projects/{project_id}/states/")
    return sorted(states, key=lambda state: state.get("sequence") or 0)


async def project_labels(api: InfinityAPI, project_id: str) -> list[dict]:
    labels, _ = await api.all_pages(f"projects/{project_id}/labels/")
    return labels


async def project_members(api: InfinityAPI, project_id: str) -> list[dict]:
    members, _ = await api.all_pages(f"projects/{project_id}/project-members-lite/")
    return [member for member in members if member.get("is_active", True) and not member.get("is_bot")]


async def project_custom_fields(api: InfinityAPI, project_id: str) -> list[dict]:
    attached = await api.get(f"projects/{project_id}/custom-fields/")
    return [item["custom_field"] for item in attached]


def pick(items: list[dict], reference: str, kind: str, *names: str) -> dict:
    """The item whose id or one of the ``names`` fields matches ``reference``."""
    for item in items:
        if item["id"] == reference or _matches(reference, *(item.get(name) for name in names)):
            return item
    known = ", ".join(str(item.get(names[0])) for item in items) or "none"
    raise InfinityAPIError(f"No {kind} '{reference}'. Available: {known}.")


async def find_people(api: InfinityAPI, project_ids: list[str], references: list[str]) -> list[str]:
    """User ids for names, emails or ids, among the members of the given projects."""
    if all(_is_uuid(reference) for reference in references):
        return references
    if not project_ids:
        raise InfinityAPIError("To find a person by name, also give the project.")
    members: dict[str, dict] = {}
    for project_id in project_ids:
        for member in await project_members(api, project_id):
            members[member["id"]] = member
    return [
        pick(list(members.values()), reference, "person", "display_name", "email", "first_name")["id"]
        if not _is_uuid(reference)
        else reference
        for reference in references
    ]
