/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { PlaneLogo } from "@plane/blocks/icons";
import { cn } from "@plane/utils";

type Props = {
  /** "panel" replaces the large illustrations, "mark" the small ones. */
  variant: "panel" | "mark";
  className?: string;
};

/**
 * Infinity Planning shows the group symbol, in the illustration colours of the theme, where Plane
 * shows its own illustrations (docs/brand/charte.md).
 */
export function InfinityEmptyMark({ variant, className }: Props) {
  if (variant === "mark")
    return (
      <div aria-hidden="true" className={cn("flex items-center justify-center", className)}>
        <PlaneLogo width="100%" height="auto" color="var(--illustration-stroke-primary)" />
      </div>
    );

  return (
    <div
      aria-hidden="true"
      className={cn(
        "relative flex aspect-[2/1] w-full items-center justify-center overflow-hidden rounded-lg border border-subtle bg-(--illustration-fill-secondary)",
        className
      )}
    >
      <PlaneLogo
        width="140%"
        height="auto"
        color="var(--illustration-fill-tertiary)"
        className="absolute top-1/2 -left-[20%] -translate-y-1/2 opacity-60"
      />
      <PlaneLogo width="34%" height="auto" color="var(--illustration-stroke-primary)" className="relative" />
    </div>
  );
}
