/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// hooks
import { useLabel } from "@/hooks/store/use-label";

type TIssueLabelChips = {
  labelIds: string[];
};

/** Read-only, one chip per label, tinted with the label color (board cards). */
export const IssueLabelChips = observer(function IssueLabelChips(props: TIssueLabelChips) {
  const { labelIds } = props;
  // store hooks
  const { getLabelById } = useLabel();

  const labels = labelIds.map((labelId) => getLabelById(labelId)).filter((label) => !!label);
  if (labels.length === 0) return null;

  return (
    <>
      {labels.map((label) => (
        <span
          key={label.id}
          className="inline-flex h-5 max-w-[160px] items-center gap-1 rounded-sm px-1.5 text-11 font-medium text-primary"
          style={{ backgroundColor: `color-mix(in srgb, ${label.color} 15%, transparent)` }}
        >
          <span className="size-1.5 flex-shrink-0 rounded-full" style={{ backgroundColor: label.color }} />
          <span className="truncate">{label.name}</span>
        </span>
      ))}
    </>
  );
});
