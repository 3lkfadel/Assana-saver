"""Compact, readable shapes for what the tools return, with links to the web app."""

import re
from html import escape
from html.parser import HTMLParser
from typing import Any

from .config import Settings

COMPLETED_GROUPS = ("completed", "cancelled")
BLOCK_TAGS = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "blockquote", "pre"}


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self.parts.append("\n- ")
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in BLOCK_TAGS and tag != "li":
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def html_to_text(html: str | None) -> str:
    """Plain text of a rich-text description or comment."""
    if not html:
        return ""
    parser = _TextExtractor()
    parser.feed(html)
    text = re.sub(r"[ \t]+\n", "\n", "".join(parser.parts))
    # A list item wrapping a paragraph: keep the bullet on the paragraph's line
    text = re.sub(r"(^|\n)-\n+", r"\1- ", text)
    # ...and no blank line between the items of a list
    text = re.sub(r"(\n- [^\n]*)\n+(?=- )", r"\1\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def task_url(settings: Settings, identifier: str) -> str:
    return f"{settings.web_url}/{settings.workspace_slug}/browse/{identifier}/"


def project_url(settings: Settings, project_id: str) -> str:
    return f"{settings.web_url}/{settings.workspace_slug}/projects/{project_id}/issues/"


def compact_task(settings: Settings, item: dict) -> dict:
    """A task from the cross-project query endpoint."""
    state = item.get("state") or {}
    return {
        "identifier": item["identifier"],
        "name": item["name"],
        "project": item["project"]["name"],
        "section": state.get("name"),
        "completed": item["completed"],
        "assignees": [person["display_name"] for person in item.get("assignees", [])],
        "due_date": item.get("target_date"),
        "start_date": item.get("start_date"),
        "priority": item.get("priority"),
        "labels": [label["name"] for label in item.get("labels", [])],
        "url": task_url(settings, item["identifier"]),
    }


def compact_project(settings: Settings, project: dict) -> dict:
    return {
        "id": project["id"],
        "identifier": project["identifier"],
        "name": project["name"],
        "description": (project.get("description") or "").strip(),
        "url": project_url(settings, project["id"]),
    }


def person(member: dict) -> dict:
    return {"id": member["id"], "name": member.get("display_name"), "email": member.get("email")}


def custom_field(field: dict) -> dict:
    shaped: dict[str, Any] = {"id": field["id"], "name": field["name"], "type": field["field_type"]}
    if field.get("options"):
        shaped["options"] = [{"id": option["id"], "name": option["name"]} for option in field["options"]]
    return shaped


def custom_field_value(field: dict, value: Any, people_by_id: dict[str, str]) -> Any:
    """A stored value in readable form: option names, people's names."""
    options = {option["id"]: option["name"] for option in field.get("options", [])}
    if field["field_type"] == "single_select":
        return options.get(value, value)
    if field["field_type"] == "multi_select":
        return [options.get(option_id, option_id) for option_id in value or []]
    if field["field_type"] == "people":
        return [people_by_id.get(user_id, user_id) for user_id in value or []]
    return value


def text_to_html(text: str) -> str:
    """Rich text from plain text: blank lines separate paragraphs, lines starting with '- ' make lists."""
    blocks = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [line.rstrip() for line in block.splitlines() if line.strip()]
        if lines and all(line.lstrip().startswith(("- ", "* ")) for line in lines):
            items = "".join(f"<li><p>{escape(line.lstrip()[2:].strip())}</p></li>" for line in lines)
            blocks.append(f"<ul>{items}</ul>")
        elif lines:
            blocks.append("<p>" + "<br>".join(escape(line) for line in lines) + "</p>")
    return "".join(blocks) or "<p></p>"
