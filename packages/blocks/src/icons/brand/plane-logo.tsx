/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";

export type PlaneLogoProps = React.ComponentPropsWithoutRef<"svg">;

// Infinity Planning mark. Kept under the historical `PlaneLogo` name so existing imports keep working.
// The mark carries its own brand colors; `color` is accepted for API compatibility but not used.
export function PlaneLogo({ width = "85", height = "45", className, x, y }: PlaneLogoProps) {
  const id = React.useId();
  return (
    <svg
      width={width}
      height={height}
      x={x}
      y={y}
      viewBox="0 0 1000 528"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <defs>
        <linearGradient id={`${id}-l`} gradientUnits="userSpaceOnUse" x1="137" y1="0" x2="500" y2="0">
          <stop offset="0" stopColor="#3D9C37" />
          <stop offset="1" stopColor="#0A2908" />
        </linearGradient>
        <linearGradient id={`${id}-r`} gradientUnits="userSpaceOnUse" x1="863" y1="0" x2="500" y2="0">
          <stop offset="0" stopColor="#3D9C37" />
          <stop offset="1" stopColor="#0A2908" />
        </linearGradient>
      </defs>
      <path d="M0 0L500 158L1000 0V528L500 370L0 528Z" fill="#3D9C37" />
      <path d="M137 43.3L500 158L137 272.7Z" fill={`url(#${id}-l)`} />
      <path d="M863 484.7L500 370L863 255.3Z" fill={`url(#${id}-r)`} />
    </svg>
  );
}
