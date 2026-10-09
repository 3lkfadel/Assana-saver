# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from importlib import import_module

import pytest
from django.apps import apps

from plane.db.models import Profile, User

migration = import_module("plane.db.migrations.0124_infinity_default_language_fr")


def make_user(email):
    return User.objects.create(email=email, username=email.split("@")[0])


@pytest.mark.unit
class TestProfileLanguage:
    @pytest.mark.django_db
    def test_new_profile_is_in_french(self):
        profile = Profile.objects.create(user=make_user("nouveau@infinity-africa.com"))

        assert profile.language == "fr"

    @pytest.mark.django_db
    def test_migration_switches_english_profiles_to_french(self):
        english = Profile.objects.create(user=make_user("anglais@infinity-africa.com"), language="en")
        spanish = Profile.objects.create(user=make_user("espagnol@infinity-africa.com"), language="es")

        migration.switch_english_profiles_to_french(apps, None)

        english.refresh_from_db()
        spanish.refresh_from_db()
        assert english.language == "fr"
        assert spanish.language == "es"
