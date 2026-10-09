/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";
import { INFINITY_BRAND_COLOR, InfinitySymbolShapes } from "./infinity-symbol";

export type PlaneLockupProps = React.ComponentPropsWithoutRef<"svg">;

/**
 * Infinity Planning lockup: the group symbol in carmine, then "Infinity Planning" on two lines in
 * the inherited font (Inter in every app). `color` sets the wordmark colour. The component keeps
 * Plane's name so that upstream security fixes still apply cleanly (ADR 0003).
 */
export function PlaneLockup({ width = "200", height = "48", className, color = "currentColor" }: PlaneLockupProps) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 200 48"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Infinity Planning"
      className={className}
    >
      <g transform="translate(0 1.25) scale(0.25)">
        <InfinitySymbolShapes color={INFINITY_BRAND_COLOR} />
      </g>
      <text x="100" y="21" fill={color} fontFamily="inherit" fontSize="21" fontWeight="700" letterSpacing="-0.3">
        Infinity
      </text>
      <text x="100" y="45" fill={color} fontFamily="inherit" fontSize="21" fontWeight="400" letterSpacing="-0.3">
        Planning
      </text>
    </svg>
  );
}
