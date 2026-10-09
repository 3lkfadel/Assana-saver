"""A project's sections, labels, members and custom fields, to turn names into the ids the API expects."""

from dataclasses import dataclass
from typing import Any

from .api import InfinityAPI, InfinityAPIError
from .resolve import (
    find_project,
    pick,
    project_custom_fields,
    project_labels,
    project_members,
    project_states,
)

COMPLETED_KINDS = ("completed", "cancelled")


@dataclass
class ProjectContext:
    project: dict
    states: list[dict]
    labels: list[dict]
    members: list[dict]
    fields: list[dict]
    me_id: str

    @classmethod
    async def load(cls, api: InfinityAPI, project_reference: str, me_id: str) -> "ProjectContext":
        project = await find_project(api, project_reference)
        return cls(
            project=project,
            states=await project_states(api, project["id"]),
            labels=await project_labels(api, project["id"]),
            members=await project_members(api, project["id"]),
            fields=await project_custom_fields(api, project["id"]),
            me_id=me_id,
        )

    @property
    def id(self) -> str:
        return self.project["id"]

    def section_id(self, name: str) -> str:
        return pick(self.states, name, "section", "name")["id"]

    def is_completed_state(self, state_id: str | None) -> bool:
        return any(state["id"] == state_id and state["group"] in COMPLETED_KINDS for state in self.states)

    def completed_section_id(self) -> str:
        for state in self.states:
            if state["group"] == "completed":
                return state["id"]
        raise InfinityAPIError(f"Project {self.project['identifier']} has no section for completed tasks.")

    def open_section_id(self) -> str:
        """The project's default section, else its first open one."""
        open_states = [state for state in self.states if state["group"] not in COMPLETED_KINDS]
        for state in open_states:
            if state.get("default"):
                return state["id"]
        if open_states:
            return open_states[0]["id"]
        raise InfinityAPIError(f"Project {self.project['identifier']} has no open section.")

    def person_id(self, reference: str) -> str:
        if reference.strip().casefold() == "me":
            return self.me_id
        return pick(self.members, reference, "project member", "display_name", "email", "first_name")["id"]

    def label_ids(self, names: list[str]) -> list[str]:
        return [pick(self.labels, name, "label", "name")["id"] for name in names]

    def custom_field_values(self, values: dict[str, Any]) -> dict[str, Any]:
        """Field id → API value, from field name → readable value (option names, people's names)."""
        converted = {}
        for name, value in values.items():
            field = pick(self.fields, name, "custom field", "name")
            converted[field["id"]] = self._field_value(field, value)
        return converted

    def _field_value(self, field: dict, value: Any) -> Any:
        if value is None or value == "" or value == []:
            return None
        kind = field["field_type"]
        if kind == "single_select":
            return pick(field["options"], str(value), f"option of {field['name']}", "name")["id"]
        if kind == "multi_select":
            names = value if isinstance(value, list) else [value]
            return [pick(field["options"], str(name), f"option of {field['name']}", "name")["id"] for name in names]
        if kind == "people":
            people = value if isinstance(value, list) else [value]
            return [self.person_id(str(person)) for person in people]
        return value
