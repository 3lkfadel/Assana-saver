"""Administration tools: projects, sections, labels, custom fields and project members."""

from typing import Annotated, Literal

from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from .. import formatting
from ..api import InfinityAPI, InfinityAPIError
from ..deps import Deps
from ..resolve import find_project, pick, project_custom_fields, project_members, project_states

WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
UPDATE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False)
DESTRUCTIVE_UPDATE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=False)

ProjectRef = Annotated[str, Field(description="Project identifier (e.g. IAT), name or id")]
SectionKind = Literal["backlog", "unstarted", "started", "completed", "cancelled"]
FieldType = Literal["text", "number", "date", "single_select", "multi_select", "people"]
Role = Literal["member", "admin"]

SECTION_COLORS = {
    "backlog": "#a3a3a3",
    "unstarted": "#3f76ff",
    "started": "#f59e0b",
    "completed": "#16a34a",
    "cancelled": "#ef4444",
}
ROLES = {"member": 15, "admin": 20}


async def _library(api: InfinityAPI) -> list[dict]:
    return await api.get("custom-fields/")


async def _find_field(api: InfinityAPI, reference: str) -> dict:
    return pick(await _library(api), reference, "custom field", "name")


async def _find_person(api: InfinityAPI, project_id: str, reference: str) -> dict:
    """A member of the project (active or not), by name, email or id."""
    members, _ = await api.all_pages(f"projects/{project_id}/project-members-lite/")
    return pick(members, reference, "project member", "display_name", "email", "first_name")


async def _find_organisation_member(api: InfinityAPI, reference: str) -> dict:
    """A member of the organisation, by name, email or id. Listing them needs organisation admin rights."""
    try:
        members, _ = await api.all_pages("members-lite/")
    except InfinityAPIError as error:
        raise InfinityAPIError(
            f"{error} Looking up people outside the project needs organisation admin rights; "
            "ask an admin to add them, or give their user id."
        ) from error
    return pick(members, reference, "member of the organisation", "display_name", "email", "first_name")


def register_admin_tools(mcp: FastMCP, deps: Deps) -> None:
    # Projects

    @mcp.tool(annotations=WRITE)
    async def create_project(
        name: Annotated[str, Field(min_length=1, max_length=255)],
        identifier: Annotated[
            str,
            Field(
                pattern=r"^[A-Za-z0-9]{1,12}$",
                description="Short code used in task identifiers, e.g. IAT for IAT-12 (letters and digits)",
            ),
        ],
        description: str = "",
    ) -> dict:
        """Create a project. The connected person becomes its admin."""
        async with deps.api() as api:
            project = await api.request(
                "POST",
                api.workspace_path("projects/"),
                json={"name": name, "identifier": identifier.upper(), "description": description},
            )
        return formatting.compact_project(deps.settings, project)

    @mcp.tool(annotations=UPDATE)
    async def update_project(
        project: ProjectRef,
        name: Annotated[str | None, Field(min_length=1, max_length=255)] = None,
        description: str | None = None,
    ) -> dict:
        """Rename a project or change its description (project admins only)."""
        changes = {key: value for key, value in (("name", name), ("description", description)) if value is not None}
        if not changes:
            raise InfinityAPIError("Nothing to change: give a name or a description.")
        async with deps.api() as api:
            found = await find_project(api, project)
            updated = await api.request("PATCH", api.workspace_path(f"projects/{found['id']}/"), json=changes)
        return formatting.compact_project(deps.settings, updated)

    # Sections and labels

    @mcp.tool(annotations=WRITE)
    async def create_section(
        project: ProjectRef,
        name: Annotated[str, Field(min_length=1, max_length=255)],
        kind: Annotated[
            SectionKind, Field(description="What tasks in it are: started, unstarted, done (completed)…")
        ] = "unstarted",
    ) -> dict:
        """Add a section (a column of the board) to a project."""
        async with deps.api() as api:
            found = await find_project(api, project)
            state = await api.request(
                "POST",
                api.workspace_path(f"projects/{found['id']}/states/"),
                json={"name": name, "group": kind, "color": SECTION_COLORS[kind]},
            )
        return {"id": state["id"], "name": state["name"], "kind": state["group"], "project": found["identifier"]}

    @mcp.tool(annotations=UPDATE)
    async def rename_section(
        project: ProjectRef,
        section: Annotated[str, Field(description="Current section name")],
        new_name: Annotated[str, Field(min_length=1, max_length=255)],
    ) -> dict:
        """Rename a section of a project."""
        async with deps.api() as api:
            found = await find_project(api, project)
            state = pick(await project_states(api, found["id"]), section, "section", "name")
            updated = await api.request(
                "PATCH", api.workspace_path(f"projects/{found['id']}/states/{state['id']}/"), json={"name": new_name}
            )
        return {"id": updated["id"], "name": updated["name"], "project": found["identifier"]}

    @mcp.tool(annotations=WRITE)
    async def create_label(
        project: ProjectRef,
        name: Annotated[str, Field(min_length=1, max_length=255)],
        color: Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$", description="Hex color")] = "#6d7b8a",
    ) -> dict:
        """Add a label to a project."""
        async with deps.api() as api:
            found = await find_project(api, project)
            label = await api.request(
                "POST", api.workspace_path(f"projects/{found['id']}/labels/"), json={"name": name, "color": color}
            )
        return {"id": label["id"], "name": label["name"], "project": found["identifier"]}

    # Custom fields

    @mcp.tool(annotations=WRITE)
    async def create_custom_field(
        name: Annotated[str, Field(min_length=1, max_length=255)],
        type: FieldType,
        options: Annotated[list[str] | None, Field(description="Option names, for list fields")] = None,
        description: str = "",
        number_precision: Annotated[int, Field(ge=0, le=6, description="Decimals of a number field")] = 0,
        add_to_projects: Annotated[list[str] | None, Field(description="Projects to add the field to")] = None,
    ) -> dict:
        """Create a custom field in the organisation's library, optionally adding it to projects."""
        async with deps.api() as api:
            field = await api.request(
                "POST",
                api.workspace_path("custom-fields/"),
                json={
                    "name": name,
                    "field_type": type,
                    "description": description,
                    "number_precision": number_precision,
                    "options": [{"name": option} for option in options or []],
                },
            )
            added = []
            for reference in add_to_projects or []:
                found = await find_project(api, reference)
                await api.request(
                    "POST",
                    api.workspace_path(f"projects/{found['id']}/custom-fields/"),
                    json={"custom_field_id": field["id"]},
                )
                added.append(found["identifier"])
        return {**formatting.custom_field(field), "projects": added}

    @mcp.tool(annotations=DESTRUCTIVE_UPDATE)
    async def update_custom_field(
        field: Annotated[str, Field(description="Custom field name or id")],
        name: Annotated[str | None, Field(min_length=1, max_length=255)] = None,
        description: str | None = None,
        options: Annotated[
            list[str] | None,
            Field(
                description=(
                    "The complete new list of options, in order. Existing options are matched by name; "
                    "options left out are removed, and so are their values on tasks: confirm with the user first."
                )
            ),
        ] = None,
    ) -> dict:
        """Rename a custom field, change its description, or change the options of a list field."""
        async with deps.api() as api:
            current = await _find_field(api, field)
            changes: dict = {key: value for key, value in (("name", name), ("description", description)) if value}
            if options is not None:
                existing = {option["name"].casefold(): option["id"] for option in current.get("options", [])}
                changes["options"] = [
                    {"id": existing[option.casefold()], "name": option}
                    if option.casefold() in existing
                    else {"name": option}
                    for option in options
                ]
            if not changes:
                raise InfinityAPIError("Nothing to change: give a name, a description or options.")
            updated = await api.request("PATCH", api.workspace_path(f"custom-fields/{current['id']}/"), json=changes)
        return formatting.custom_field(updated)

    @mcp.tool(annotations=UPDATE)
    async def add_custom_field_to_project(
        project: ProjectRef, field: Annotated[str, Field(description="Custom field name or id")]
    ) -> dict:
        """Show a custom field of the library on a project's tasks."""
        async with deps.api() as api:
            found = await find_project(api, project)
            current = await _find_field(api, field)
            await api.request(
                "POST",
                api.workspace_path(f"projects/{found['id']}/custom-fields/"),
                json={"custom_field_id": current["id"]},
            )
        return {"project": found["identifier"], "added": current["name"]}

    @mcp.tool(annotations=UPDATE)
    async def remove_custom_field_from_project(
        project: ProjectRef, field: Annotated[str, Field(description="Custom field name or id")]
    ) -> dict:
        """Hide a custom field on a project's tasks. Its values are kept and come back if it is added again."""
        async with deps.api() as api:
            found = await find_project(api, project)
            current = pick(await project_custom_fields(api, found["id"]), field, "custom field of the project", "name")
            await api.request("DELETE", api.workspace_path(f"projects/{found['id']}/custom-fields/{current['id']}/"))
        return {"project": found["identifier"], "removed": current["name"]}

    # Project members

    @mcp.tool(annotations=UPDATE)
    async def add_project_member(
        project: ProjectRef,
        person: Annotated[str, Field(description="Name, email or user id of a member of the organisation")],
        role: Role = "member",
    ) -> dict:
        """Add a person of the organisation to a project (project admins only)."""
        async with deps.api() as api:
            found = await find_project(api, project)
            member = await _find_organisation_member(api, person)
            await api.request(
                "POST",
                api.workspace_path(f"projects/{found['id']}/members/"),
                json={"member": member["id"], "role": ROLES[role]},
            )
        return {"project": found["identifier"], "added": member.get("display_name"), "role": role}

    @mcp.tool(annotations=UPDATE)
    async def set_project_member_role(project: ProjectRef, person: str, role: Role) -> dict:
        """Make a project member an admin of the project, or a plain member (project admins only)."""
        async with deps.api() as api:
            found = await find_project(api, project)
            member = await _find_person(api, found["id"], person)
            await api.request(
                "PATCH",
                api.workspace_path(f"projects/{found['id']}/members/{member['membership_id']}/"),
                json={"role": ROLES[role]},
            )
        return {"project": found["identifier"], "person": member.get("display_name"), "role": role}

    @mcp.tool(annotations=DESTRUCTIVE_UPDATE)
    async def remove_project_member(project: ProjectRef, person: str) -> dict:
        """Remove a person from a project (project admins only). Their tasks stay; confirm with the user first."""
        async with deps.api() as api:
            found = await find_project(api, project)
            member = await _find_person(api, found["id"], person)
            await api.request(
                "DELETE", api.workspace_path(f"projects/{found['id']}/members/{member['membership_id']}/")
            )
            remaining = await project_members(api, found["id"])
        return {
            "project": found["identifier"],
            "removed": member.get("display_name"),
            "members": [person.get("display_name") for person in remaining],
        }
