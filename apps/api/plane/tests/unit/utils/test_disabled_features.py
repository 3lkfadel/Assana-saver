# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from rest_framework import serializers

from plane.app.serializers.base import NoGuestRoleMixin
from plane.utils.disabled_features import GUEST_ROLE_DISABLED_ERROR, is_guest_role


@pytest.mark.unit
class TestIsGuestRole:
    @pytest.mark.parametrize("role", [5, "5"])
    def test_guest_role(self, role):
        assert is_guest_role(role) is True

    @pytest.mark.parametrize("role", [15, 20, "15", None, "", "admin"])
    def test_other_values(self, role):
        assert is_guest_role(role) is False


@pytest.mark.unit
class TestNoGuestRoleMixin:
    def test_refuses_guest_role(self):
        with pytest.raises(serializers.ValidationError) as error:
            NoGuestRoleMixin().validate_role(5)
        assert GUEST_ROLE_DISABLED_ERROR in str(error.value)

    def test_keeps_member_role(self):
        assert NoGuestRoleMixin().validate_role(15) == 15
