/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { PropertiesOutline } from "@makeplane/propel/icons";
import { useTranslation } from "@plane/i18n";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// components
import { IssueActivityBlockComponent } from "./";

type TIssueCustomFieldActivity = { activityId: string; ends: "top" | "bottom" | undefined };

/** "set Budget to 95" / "cleared Budget": the field name is stored in the activity comment. */
export const IssueCustomFieldActivity = observer(function IssueCustomFieldActivity(props: TIssueCustomFieldActivity) {
  const { activityId, ends } = props;
  const { t } = useTranslation();
  const {
    activity: { getActivityById },
  } = useIssueDetail();

  const activity = getActivityById(activityId);
  if (!activity) return <></>;

  const field = activity.comment ?? "";
  return (
    <IssueActivityBlockComponent
      icon={<PropertiesOutline className="h-3.5 w-3.5 text-secondary" aria-hidden="true" />}
      activityId={activityId}
      ends={ends}
    >
      <>
        {activity.new_value
          ? t("custom_fields.activity.set", { field, value: activity.new_value })
          : t("custom_fields.activity.cleared", { field })}
      </>
    </IssueActivityBlockComponent>
  );
});
