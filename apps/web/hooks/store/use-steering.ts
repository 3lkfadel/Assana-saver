/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useContext } from "react";
// mobx store
import { StoreContext } from "@/lib/store-context";
// types
import type { ISteeringStore } from "@/store/steering.store";

export const useSteering = (): ISteeringStore => {
  const context = useContext(StoreContext);
  if (context === undefined) throw new Error("useSteering must be used within StoreProvider");
  return context.steering;
};
