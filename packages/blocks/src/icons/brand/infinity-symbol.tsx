/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";

/** Carmine of Infinity Africa Group, reserved for brand moments (docs/brand/charte.md). */
export const INFINITY_BRAND_COLOR = "#DC143C";

/** Native size of the Infinity symbol drawing, in user units. */
export const INFINITY_SYMBOL_WIDTH = 347;
export const INFINITY_SYMBOL_HEIGHT = 182;

type InfinitySymbolShapesProps = {
  color: string;
};

/**
 * The Infinity Africa Group symbol, drawn in a 347 × 182 box: a band rising to the right between
 * two triangles that fade towards the centre. Mirrors docs/brand/logo/symbole-*.svg.
 */
export function InfinitySymbolShapes({ color }: InfinitySymbolShapesProps) {
  const id = React.useId();
  const left = `${id}-left`;
  const right = `${id}-right`;
  return (
    <>
      <defs>
        <linearGradient id={left} x1="0" y1="0" x2="172" y2="0" gradientUnits="userSpaceOnUse">
          <stop offset="0.27" stopColor={color} />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
        <linearGradient id={right} x1="347" y1="0" x2="175" y2="0" gradientUnits="userSpaceOnUse">
          <stop offset="0.27" stopColor={color} />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points="0,0 172,56 0,140" fill={`url(#${left})`} />
      <polygon points="347,182 175,126 347,40" fill={`url(#${right})`} />
      <polygon points="0,110 347,0 347,71 0,182" fill={color} />
    </>
  );
}
