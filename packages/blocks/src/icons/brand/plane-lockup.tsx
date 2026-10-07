/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";
import { PlaneLogo } from "./plane-logo";

export type PlaneLockupProps = React.ComponentPropsWithoutRef<"svg">;

// Infinity Planning lockup (mark + wordmark). Kept under the historical `PlaneLockup` name so existing imports
// keep working. The wordmark follows `color` (defaults to the current text color) so it adapts to light/dark themes.
export function PlaneLockup({ width = "380", height = "44", className, color = "currentColor" }: PlaneLockupProps) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 380 44"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role="img"
      aria-label="Infinity Planning"
    >
      <PlaneLogo x={0} y={0} width={83} height={44} />
      <text
        x={96}
        y={33}
        fill={color}
        fontFamily="inherit"
        fontSize={30}
        fontWeight={600}
        textLength={280}
        lengthAdjust="spacingAndGlyphs"
      >
        Infinity Planning
      </text>
    </svg>
  );
}
