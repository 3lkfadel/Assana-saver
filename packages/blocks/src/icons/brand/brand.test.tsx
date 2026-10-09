/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { INFINITY_BRAND_COLOR } from "./infinity-symbol";
import { PlaneLockup } from "./plane-lockup";
import { PlaneLogo } from "./plane-logo";

afterEach(cleanup);

describe("Infinity Planning brand marks", () => {
  it("renders the lockup with the Infinity Planning wordmark", () => {
    render(<PlaneLockup />);
    const logo = screen.getByRole("img", { name: "Infinity Planning" });
    expect(logo.textContent).toBe("InfinityPlanning");
  });

  it("draws the lockup symbol in the group carmine and the wordmark in the given colour", () => {
    const { container } = render(<PlaneLockup color="#2A2D2F" />);
    expect(container.querySelector("polygon:last-of-type")?.getAttribute("fill")).toBe(INFINITY_BRAND_COLOR);
    container.querySelectorAll("text").forEach((text) => expect(text.getAttribute("fill")).toBe("#2A2D2F"));
  });

  it("renders the symbol alone, in carmine by default", () => {
    const { container } = render(<PlaneLogo />);
    expect(screen.getByRole("img", { name: "Infinity Planning" })).toBeTruthy();
    expect(container.querySelector("text")).toBeNull();
    expect(container.querySelector("polygon:last-of-type")?.getAttribute("fill")).toBe(INFINITY_BRAND_COLOR);
  });

  it("gives each rendered symbol its own gradient ids", () => {
    const { container } = render(
      <>
        <PlaneLogo />
        <PlaneLogo />
      </>
    );
    const ids = Array.from(container.querySelectorAll("linearGradient")).map((g) => g.id);
    expect(new Set(ids).size).toBe(4);
  });

  it("contains no Plane artwork", () => {
    const { container } = render(<PlaneLockup />);
    expect(container.innerHTML).not.toContain("Plane");
  });
});
