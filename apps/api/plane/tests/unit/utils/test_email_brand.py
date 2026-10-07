# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string
from django.test import override_settings

from plane.utils.templatetags.email_brand import email_logo_url

# BASE_DIR is apps/api/plane; the e-mail templates live in apps/api/templates.
EMAIL_TEMPLATES_DIR = Path(settings.BASE_DIR).parent / "templates" / "emails"
EMAIL_TEMPLATES = sorted(p.relative_to(EMAIL_TEMPLATES_DIR.parent).as_posix() for p in EMAIL_TEMPLATES_DIR.rglob("*.html"))


@pytest.mark.unit
@pytest.mark.parametrize("template_name", EMAIL_TEMPLATES)
def test_email_template_is_branded_infinity_planning(template_name):
    html = render_to_string(template_name, {})

    assert "Infinity Planning" in html
    assert re.search(r"\bPlane\b", html) is None
    for host in ("plane.so", "plane.sh", "github.com/makeplane", "mailinblue.com"):
        assert host not in html


@pytest.mark.unit
@override_settings(WEB_URL="https://planning.infinity-africa.com/", STATIC_URL="/static/")
def test_email_logo_url_is_absolute_on_web_url():
    assert email_logo_url() == "https://planning.infinity-africa.com/static/emails/infinity-planning-logo.png"
    assert email_logo_url("dark") == "https://planning.infinity-africa.com/static/emails/infinity-planning-logo-white.png"


@pytest.mark.unit
def test_email_logos_are_shipped_as_static_files():
    static_dir = Path(settings.BASE_DIR) / "static" / "emails"
    assert (static_dir / "infinity-planning-logo.png").is_file()
    assert (static_dir / "infinity-planning-logo-white.png").is_file()
