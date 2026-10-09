# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Plane features that Infinity Planning switches off.

Infinity Planning has no cycles, modules, estimates or Guest role: every account is a
group member. The API refuses to turn these features back on.
"""

GUEST_ROLE = 5
DEFAULT_MEMBER_ROLE = 15

GUEST_ROLE_DISABLED_ERROR = "The Guest role is disabled in Infinity Planning"
ESTIMATES_DISABLED_ERROR = "Estimates are disabled in Infinity Planning"

# Project fields the API exposes but never lets a client change.
DISABLED_PROJECT_FIELDS = ["cycle_view", "module_view", "estimate"]


def is_guest_role(role):
    """Return True when a requested role is the disabled Guest role."""
    try:
        return int(role) == GUEST_ROLE
    except (TypeError, ValueError):
        return False
