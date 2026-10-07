/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";
import {
  INFINITY_BRAND_COLOR,
  INFINITY_SYMBOL_HEIGHT,
  INFINITY_SYMBOL_WIDTH,
  InfinitySymbolShapes,
} from "./infinity-symbol";

export type PlaneLogoProps = React.ComponentPropsWithoutRef<"svg">;

/**
 * Infinity Planning symbol. The component keeps Plane's name so that upstream security fixes
 * still apply cleanly (ADR 0003); the default colour is the group carmine.
 */
export function PlaneLogo({ width = "85", height = "45", className, color = INFINITY_BRAND_COLOR }: PlaneLogoProps) {
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${INFINITY_SYMBOL_WIDTH} ${INFINITY_SYMBOL_HEIGHT}`}
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Infinity Planning"
      className={className}
    >
      <InfinitySymbolShapes color={color} />
    </svg>
  );
}
