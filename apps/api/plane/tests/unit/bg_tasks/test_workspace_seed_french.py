# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.bgtasks.workspace_seed_task import workspace_seed
from plane.db.models import Issue, Label, Page, State


@pytest.mark.unit
class TestWorkspaceSeedFrench:
    @pytest.mark.django_db
    def test_demo_content_is_in_french_without_plane(self, workspace):
        workspace_seed(workspace.id)

        issue_names = list(Issue.objects.filter(workspace=workspace).values_list("name", flat=True))
        assert "Bienvenue sur Infinity Planning" in issue_names
        assert set(State.objects.filter(workspace=workspace).values_list("name", flat=True)) == {
            "À planifier",
            "À faire",
            "En cours",
            "Terminé",
            "Annulé",
        }
        assert "prise en main" in Label.objects.filter(workspace=workspace).values_list("name", flat=True)

        texts = issue_names + [
            text
            for issue in Issue.objects.filter(workspace=workspace)
            for text in (issue.description_html, issue.description_stripped)
        ]
        texts += [page.name + page.description_html for page in Page.objects.filter(workspace=workspace)]
        assert not [text for text in texts if "Plane" in text or "plane.so" in text]
