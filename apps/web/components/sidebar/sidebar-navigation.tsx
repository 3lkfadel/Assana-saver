/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { cn } from "@plane/utils";

type TSidebarNavItem = {
  className?: string;
  isActive?: boolean;
  children?: React.ReactNode;
};

export function SidebarNavItem(props: TSidebarNavItem) {
  const { className, isActive, children } = props;
  return (
    <div
      className={cn(
        "group relative flex w-full cursor-pointer items-center justify-between gap-1.5 rounded-md px-2 py-1 outline-none",
        {
          // The active item is a frost white pill on the anthracite navigation (infinity-nav.css).
          "ip-nav-on !bg-(--ip-nav-on) text-primary shadow-raised-100": isActive,
          "text-secondary hover:bg-layer-transparent-hover active:bg-layer-transparent-active": !isActive,
        },
        className
      )}
    >
      {children}
    </div>
  );
}
