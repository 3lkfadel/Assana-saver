/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TSelectionHelper } from "@/hooks/use-multiple-select";

type Props = {
  className?: string;
  selectionHelpers: TSelectionHelper;
};

/**
 * Bulk-actions bar shown while work items are selected. Plane's community edition only shipped an
 * upgrade banner here; Infinity Planning removed it, and the real toolbar comes with the bulk
 * operations work (selection stays off until then, see hooks/use-bulk-operation-status.ts).
 */
export function IssueBulkOperationsRoot(_props: Props) {
  return null;
}
