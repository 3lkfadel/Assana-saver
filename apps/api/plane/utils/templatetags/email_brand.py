# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django import template
from django.conf import settings

register = template.Library()

EMAIL_LOGOS = {
    "light": "emails/infinity-planning-logo.png",
    "dark": "emails/infinity-planning-logo-white.png",
}


@register.simple_tag
def email_logo_url(background="light"):
    """Absolute URL of the Infinity Planning logo for e-mails.

    E-mails are read outside the app, so the URL is built from WEB_URL; the proxy serves
    /static/* from the API. `background` is the colour behind the logo ("light" or "dark").
    """
    path = f"{settings.STATIC_URL.rstrip('/')}/{EMAIL_LOGOS[background]}"
    return f"{(settings.WEB_URL or '').rstrip('/')}{path}"
