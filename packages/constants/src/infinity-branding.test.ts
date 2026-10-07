/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import * as constants from "./index";
import { SITE_DESCRIPTION, SITE_NAME, SITE_TITLE, SPACE_SITE_NAME, SPACE_SITE_TITLE } from "./metadata";
import { GROUPED_WORKSPACE_SETTINGS, WORKSPACE_SETTINGS } from "./settings/workspace";

describe("Infinity Planning metadata", () => {
  it("names the product Infinity Planning in every app", () => {
    for (const name of [SITE_NAME, SITE_TITLE, SPACE_SITE_NAME, SPACE_SITE_TITLE]) {
      expect(name).toBe("Infinity Planning");
    }
  });

  it("describes the product without Plane", () => {
    expect(SITE_DESCRIPTION).toContain("Infinity Africa Group");
    expect(SITE_DESCRIPTION).not.toMatch(/plane/i);
  });
});

describe("paid edition removal", () => {
  it("offers no billing page in the workspace settings", () => {
    expect(Object.keys(WORKSPACE_SETTINGS)).not.toContain("billing-and-plans");
    const hrefs = Object.values(GROUPED_WORKSPACE_SETTINGS)
      .flat()
      .map((item) => item.href);
    expect(hrefs).not.toContain("/settings/billing");
  });

  it("exports no subscription or checkout constants", () => {
    const names = Object.keys(constants);
    for (const removed of [
      "SUBSCRIPTION_REDIRECTION_URLS",
      "SUBSCRIPTION_WEBPAGE_URLS",
      "TALK_TO_SALES_URL",
      "PLANE_COMMUNITY_PRODUCTS",
    ]) {
      expect(names).not.toContain(removed);
    }
  });
});
