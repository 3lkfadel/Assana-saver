/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { afterEach, describe, expect, it } from "vitest";
import {
  formatDateRange,
  renderFormattedDate,
  renderFormattedDateWithoutYear,
  renderFormattedPayloadDate,
  setDateLocale,
} from "./datetime";

const date = new Date(2026, 9, 7, 14, 30);

describe("date language", () => {
  afterEach(() => setDateLocale("en"));

  it("formats dates in English by default", () => {
    expect(renderFormattedDate(date)).toBe("Oct 07, 2026");
    expect(renderFormattedDateWithoutYear(date)).toBe("Oct 07");
  });

  it("formats dates day first with French month names in French", () => {
    setDateLocale("fr");

    expect(renderFormattedDate(date)).toBe("07 oct. 2026");
    expect(renderFormattedDateWithoutYear(date)).toBe("07 oct.");
    expect(formatDateRange(date, new Date(2026, 9, 12))).toBe("07 - 12 oct. 2026");
  });

  it("keeps payload dates in ISO format", () => {
    setDateLocale("fr");

    expect(renderFormattedPayloadDate(date)).toBe("2026-10-07");
  });
});
