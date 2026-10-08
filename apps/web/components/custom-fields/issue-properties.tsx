/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
// components
import { SidebarPropertyListItem } from "@/components/common/layout/sidebar/property-list-item";
// hooks
import { useCustomField } from "@/hooks/store/use-custom-field";
// local imports
import { useProjectCustomFields } from "./use-project-custom-fields";
import { CUSTOM_FIELD_TYPE_ICONS, CustomFieldValueEditor } from "./value-editor";

type TIssueCustomFieldPropertiesProps = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  disabled?: boolean;
};

/** One sidebar row per custom field of the work item's project. */
export const IssueCustomFieldProperties = observer(function IssueCustomFieldProperties(
  props: TIssueCustomFieldPropertiesProps
) {
  const { workspaceSlug, projectId, issueId, disabled } = props;
  const { t } = useTranslation();
  const { getValue, setValue } = useCustomField();
  const fields = useProjectCustomFields(workspaceSlug, projectId);

  return (
    <>
      {fields.map((field) => (
        <SidebarPropertyListItem key={field.id} icon={CUSTOM_FIELD_TYPE_ICONS[field.field_type]} label={field.name}>
          <CustomFieldValueEditor
            field={field}
            value={getValue(issueId, field.id)}
            projectId={projectId}
            disabled={disabled}
            onChange={(value) =>
              setValue(workspaceSlug, projectId, issueId, field.id, value).catch(() =>
                setToast({ type: "error", title: t("common.error.label"), message: t("custom_fields.errors.value") })
              )
            }
          />
        </SidebarPropertyListItem>
      ))}
    </>
  );
});
