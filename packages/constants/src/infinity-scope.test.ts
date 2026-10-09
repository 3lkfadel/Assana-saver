/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { EUserWorkspaceRoles } from "@plane/types";
import { GROUPED_PROJECT_SETTINGS, PROJECT_SETTINGS } from "./settings/project";
import { ASSIGNABLE_ROLE, ROLE } from "./workspace";

describe("project settings without cycles, modules and estimates", () => {
  it("has no settings page for them", () => {
    for (const key of ["features_cycles", "features_modules", "estimates"]) {
      expect(Object.keys(PROJECT_SETTINGS)).not.toContain(key);
    }
  });

  it("links to none of them from the settings sidebar", () => {
    const hrefs = Object.values(GROUPED_PROJECT_SETTINGS)
      .flat()
      .map((item) => item.href);
    expect(hrefs).not.toContain("/features/cycles");
    expect(hrefs).not.toContain("/features/modules");
    expect(hrefs).not.toContain("/estimates");
  });
});

describe("roles without Guest", () => {
  it("only offers Member and Admin", () => {
    expect(Object.keys(ASSIGNABLE_ROLE).map(Number).toSorted()).toEqual([
      EUserWorkspaceRoles.MEMBER,
      EUserWorkspaceRoles.ADMIN,
    ]);
  });

  it("still has a label for every stored role", () => {
    expect(ROLE[EUserWorkspaceRoles.GUEST]).toBe("Guest");
  });
});
