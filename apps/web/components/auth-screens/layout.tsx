/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";
import { PlaneLockup, PlaneLogo } from "@plane/blocks/icons";

type AuthScreenLayoutProps = {
  children: React.ReactNode;
};

/**
 * Sign-in, sign-up and password screens: an anthracite brand panel with the group symbol in carmine
 * (docs/brand/charte.md) beside the form. The panel is hidden on narrow screens.
 */
export function AuthScreenLayout({ children }: AuthScreenLayoutProps) {
  return (
    <div className="relative z-10 flex h-screen w-screen overflow-hidden bg-surface-1">
      <aside className="ip-nav relative hidden w-[42%] max-w-[40rem] shrink-0 flex-col justify-between overflow-hidden bg-canvas p-10 lg:flex">
        <PlaneLockup height={36} width={150} color="var(--txt-primary)" className="relative" />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 -left-[22%] w-[150%] -translate-y-1/3 motion-safe:animate-[ip-symbol-sweep_900ms_cubic-bezier(0.2,0.7,0.2,1)]"
        >
          <PlaneLogo width="100%" height="auto" />
        </div>
        <p className="relative text-body-sm-regular text-tertiary">Infinity Africa Group</p>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col items-center overflow-y-auto px-8 pt-6 pb-10">{children}</div>
    </div>
  );
}
