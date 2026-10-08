/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { useTranslation } from "@plane/i18n";
// hooks
import { useCustomField } from "@/hooks/store/use-custom-field";
import { useMember } from "@/hooks/store/use-member";
// local imports
import { useProjectCustomFields } from "./use-project-custom-fields";
import { formatCustomFieldValue } from "./value-editor";

const chipClassName = "inline-flex h-5 max-w-[180px] items-center gap-1 rounded-sm px-1.5 text-11 font-medium";

type TIssueCustomFieldChipsProps = {
  projectId: string;
  issueId: string;
};

/** Read-only chips for the custom fields that hold a value (board cards). */
export const IssueCustomFieldChips = observer(function IssueCustomFieldChips(props: TIssueCustomFieldChipsProps) {
  const { projectId, issueId } = props;
  const { workspaceSlug } = useParams();
  const { currentLocale } = useTranslation();
  const { getValue } = useCustomField();
  const { getUserDetails } = useMember();
  const fields = useProjectCustomFields(workspaceSlug?.toString(), projectId);

  return (
    <>
      {fields.map((field) => {
        const value = getValue(issueId, field.id);
        if (field.field_type === "single_select" || field.field_type === "multi_select") {
          const ids = Array.isArray(value) ? value : value ? [String(value)] : [];
          return field.options
            .filter((option) => ids.includes(option.id))
            .map((option) => (
              <span
                key={`${field.id}-${option.id}`}
                title={field.name}
                className={`${chipClassName} text-primary`}
                style={{ backgroundColor: `color-mix(in srgb, ${option.color || "#888"} 18%, transparent)` }}
              >
                {option.name}
              </span>
            ));
        }
        const text =
          field.field_type === "people" && Array.isArray(value)
            ? value
                .map((userId) => getUserDetails(userId)?.display_name)
                .filter(Boolean)
                .join(", ")
            : formatCustomFieldValue(field, value, currentLocale);
        if (!text) return null;
        return (
          <span key={field.id} title={field.name} className={`${chipClassName} bg-layer-1 text-secondary`}>
            <span className="text-tertiary">{field.name}</span>
            <span className="truncate text-primary">{text}</span>
          </span>
        );
      })}
    </>
  );
});
