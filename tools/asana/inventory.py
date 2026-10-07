#!/usr/bin/env python3
"""Read-only inventory of an Asana organization, used to prioritise Asana-saver work.

Counts how the organization actually uses Asana (teams, projects, sections, multi-homing,
custom field types, milestones, approvals, dependencies, goals, templates...) without
storing any task names or descriptions.

Usage:
    echo 'ASANA_PAT=<personal access token>' > .env.asana
    python3 -I tools/asana/inventory.py [--env .env.asana] [--out .asana-inventory]

Only GET requests are sent. The token is read from the env file and never printed.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

API = "https://app.asana.com/api/1.0"


def load_token(env_path):
    if not os.path.exists(env_path):
        sys.exit(f"Fichier {env_path} introuvable : créez-le avec une ligne ASANA_PAT=<jeton>.")
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            key, _, value = line.strip().partition("=")
            if key == "ASANA_PAT" and value:
                return value.strip().strip('"').strip("'")
    sys.exit(f"Aucune ligne ASANA_PAT=... dans {env_path}.")


class Client:
    def __init__(self, token):
        self.token = token
        self.calls = 0

    def get(self, path, params=None):
        url = f"{API}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        while True:
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.token}"})
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    self.calls += 1
                    return json.load(resp)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(int(e.headers.get("Retry-After", "30")))
                    continue
                if e.code in (400, 402, 403, 404):
                    try:
                        detail = "; ".join(err.get("message", "") for err in json.load(e).get("errors", []))
                    except ValueError:
                        detail = ""
                    print(f"[ignoré] HTTP {e.code} sur {path} : {detail}", file=sys.stderr)
                    return None
                raise

    def paginate(self, path, params):
        params = dict(params, limit=100)
        while True:
            page = self.get(path, params)
            if page is None:
                return
            yield from page.get("data", [])
            nxt = page.get("next_page")
            if not nxt or not nxt.get("offset"):
                return
            params["offset"] = nxt["offset"]


TASK_FIELDS = ",".join([
    "resource_subtype", "completed", "assignee", "followers", "parent", "num_subtasks",
    "memberships.project", "memberships.section", "dependencies", "dependents",
    "start_on", "due_on", "due_at", "tags", "custom_fields.resource_subtype",
    "num_likes", "approval_status",
])


def inventory(client):
    me = client.get("/users/me", {"opt_fields": "workspaces.name,workspaces.is_organization"})["data"]
    report = {"workspaces": []}

    for ws in me["workspaces"]:
        ws_gid = ws["gid"]
        w = {"name": ws["name"], "is_organization": ws.get("is_organization", False)}

        teams = list(client.paginate(f"/users/me/teams", {"organization": ws_gid, "opt_fields": "name"})) \
            if w["is_organization"] else []
        w["teams_visible"] = len(teams)

        projects = list(client.paginate("/projects", {
            "workspace": ws_gid,
            "opt_fields": "name,archived,team.name,default_view,is_template,members,"
                          "custom_field_settings.custom_field.resource_subtype,start_on,due_on",
        }))
        w["projects"] = {
            "total": len(projects),
            "archived": sum(p.get("archived", False) for p in projects),
            "default_view": dict(Counter(p.get("default_view") for p in projects)),
            "with_dates": sum(bool(p.get("start_on") or p.get("due_on")) for p in projects),
        }
        per_team = Counter((p.get("team") or {}).get("name", "(sans équipe)") for p in projects)
        w["projects_per_team"] = dict(per_team.most_common())

        cf_types_on_projects = Counter()
        for p in projects:
            for s in p.get("custom_field_settings") or []:
                cf_types_on_projects[s["custom_field"].get("resource_subtype")] += 1
        w["custom_field_types_on_projects"] = dict(cf_types_on_projects)

        sections_per_project = []
        tasks = {}
        for p in projects:
            if p.get("archived"):
                continue
            sections_per_project.append(len(list(client.paginate(f"/projects/{p['gid']}/sections", {}))))
            for t in client.paginate("/tasks", {"project": p["gid"], "opt_fields": TASK_FIELDS}):
                tasks[t["gid"]] = t
                if t.get("num_subtasks"):
                    for st in client.paginate(f"/tasks/{t['gid']}/subtasks", {"opt_fields": TASK_FIELDS}):
                        tasks.setdefault(st["gid"], st)

        tl = list(tasks.values())
        top = [t for t in tl if not t.get("parent")]
        sub = [t for t in tl if t.get("parent")]
        memberships = Counter(len(t.get("memberships") or []) for t in tl)
        cf_values = Counter(cf.get("resource_subtype") for t in tl for cf in t.get("custom_fields") or [])
        w["sections_per_active_project"] = {
            "min": min(sections_per_project, default=0),
            "max": max(sections_per_project, default=0),
            "avg": round(sum(sections_per_project) / len(sections_per_project), 1) if sections_per_project else 0,
        }
        w["tasks"] = {
            "total_seen": len(tl),
            "top_level": len(top),
            "subtasks": len(sub),
            "subtasks_also_in_a_project": sum(bool(t.get("memberships")) for t in sub),
            "completed": sum(t.get("completed", False) for t in tl),
            "by_type": dict(Counter(t.get("resource_subtype") for t in tl)),
            "projects_per_task": {str(k): v for k, v in sorted(memberships.items())},
            "multi_homed": sum(n for k, n in memberships.items() if k >= 2),
            "with_assignee": sum(bool(t.get("assignee")) for t in tl),
            "avg_followers": round(sum(len(t.get("followers") or []) for t in tl) / len(tl), 2) if tl else 0,
            "with_dependencies": sum(bool(t.get("dependencies") or t.get("dependents")) for t in tl),
            "with_start_date": sum(bool(t.get("start_on")) for t in tl),
            "with_due_time": sum(bool(t.get("due_at")) for t in tl),
            "with_tags": sum(bool(t.get("tags")) for t in tl),
            "custom_field_values_by_type": dict(cf_values),
        }

        custom_fields = list(client.paginate(f"/workspaces/{ws_gid}/custom_fields", {"opt_fields": "resource_subtype"}))
        w["custom_fields_library"] = dict(Counter(cf.get("resource_subtype") for cf in custom_fields))

        goals = list(client.paginate("/goals", {"workspace": ws_gid, "opt_fields": "parent_goal,metric"}))
        w["goals"] = {"total_visible": len(goals), "with_parent": sum(bool(g.get("parent_goal")) for g in goals),
                      "with_metric": sum(bool(g.get("metric")) for g in goals)}

        portfolios = list(client.paginate("/portfolios", {"workspace": ws_gid, "owner": "me"}))
        w["portfolios_owned_by_me"] = len(portfolios)

        templates = list(client.paginate("/project_templates", {"workspace": ws_gid}))
        w["project_templates_visible"] = len(templates)

        tags = list(client.paginate(f"/workspaces/{ws_gid}/tags", {}))
        w["tags_total"] = len(tags)

        report["workspaces"].append(w)

    report["api_calls"] = client.calls
    report["not_measurable_via_api"] = ["règles", "formulaires", "récurrence des tâches", "bundles", "dashboards"]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env", default=".env.asana")
    parser.add_argument("--out", default=".asana-inventory")
    args = parser.parse_args()

    client = Client(load_token(args.env))
    report = inventory(client)
    os.makedirs(args.out, exist_ok=True)
    out_file = os.path.join(args.out, "summary.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Inventaire écrit dans {out_file} ({report['api_calls']} appels API).")


if __name__ == "__main__":
    main()
