/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { StateOutline } from "@makeplane/propel/icons";
import { useTranslation } from "@plane/i18n";
import { renderFormattedDate } from "@plane/utils";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// components
import { IssueActivityBlockComponent } from "./";

type TIssueSteeringActivity = { activityId: string; ends: "top" | "bottom" | undefined };

const CHOICE_PREFIXES: Record<string, string> = {
  status: "steering.task.status",
  waiting_for: "steering.task.waiting_for",
  risk_nature: "steering.task.risk",
};

/** "set Status to In progress" / "cleared Supervisor": the steering field key is stored in the activity comment. */
export const IssueSteeringActivity = observer(function IssueSteeringActivity(props: TIssueSteeringActivity) {
  const { activityId, ends } = props;
  const { t } = useTranslation();
  const {
    activity: { getActivityById },
  } = useIssueDetail();

  const activity = getActivityById(activityId);
  if (!activity) return <></>;

  const key = activity.comment ?? "";
  const field = t(`steering.task.fields.${key.replace(/_id$/, "")}`);
  const raw = activity.new_value;
  let value = raw ?? "";
  if (raw && CHOICE_PREFIXES[key]) value = t(`${CHOICE_PREFIXES[key]}.${raw}`);
  else if (raw && key === "progress") value = `${raw} %`;
  else if (raw && (key === "risk_effective_date" || key === "closure_date")) value = renderFormattedDate(raw) ?? raw;

  return (
    <IssueActivityBlockComponent
      icon={<StateOutline className="h-3.5 w-3.5 text-secondary" aria-hidden="true" />}
      activityId={activityId}
      ends={ends}
    >
      <>{raw ? t("steering.task.activity.set", { field, value }) : t("steering.task.activity.cleared", { field })}</>
    </IssueActivityBlockComponent>
  );
});
