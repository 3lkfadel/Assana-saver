/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import type { KeyboardEvent } from "react";
import { observer } from "mobx-react";
import {
  CalendarOutline,
  DropdownOutline,
  HashOutline,
  ListOutline,
  MembersOutline,
  TextOutline,
} from "@makeplane/propel/icons";
import { DateSelect } from "@plane/blocks/property-select";
import { Select } from "@plane/blocks/select";
import { useTranslation } from "@plane/i18n";
import { cn, getDate, renderFormattedPayloadDate } from "@plane/utils";
// components
import { MemberSelect } from "@/components/dropdowns/member/member-select";
// types
import type {
  TCustomField,
  TCustomFieldOption,
  TCustomFieldType,
  TCustomFieldValue,
} from "@/services/custom-field.service";

export const CUSTOM_FIELD_TYPE_ICONS: Record<TCustomFieldType, React.FC<{ className?: string }>> = {
  text: TextOutline,
  number: HashOutline,
  date: CalendarOutline,
  single_select: DropdownOutline,
  multi_select: ListOutline,
  people: MembersOutline,
};

export function OptionDot({ color }: { color?: string }) {
  return <span className="size-2 shrink-0 rounded-full" style={{ backgroundColor: color || "var(--text-tertiary)" }} />;
}

/** Formats a stored value for display (cards, read-only places). */
export function formatCustomFieldValue(
  field: TCustomField,
  value: TCustomFieldValue,
  locale: string | undefined
): string | undefined {
  if (value === null || value === "" || (Array.isArray(value) && value.length === 0)) return undefined;
  if (field.field_type === "number" && typeof value === "number")
    return value.toLocaleString(locale, {
      minimumFractionDigits: field.number_precision,
      maximumFractionDigits: field.number_precision,
    });
  if (field.field_type === "date" && typeof value === "string")
    return getDate(value)?.toLocaleDateString(locale, { day: "numeric", month: "short", year: "numeric" });
  return String(value);
}

const textInputClassName =
  "h-7.5 w-full min-w-0 rounded-sm bg-transparent px-2 text-body-xs-regular text-primary outline-none placeholder:text-placeholder hover:bg-layer-transparent-hover focus:bg-layer-transparent-hover disabled:cursor-not-allowed";

type TInlineInputProps = {
  value: string;
  placeholder: string;
  disabled?: boolean;
  inputMode?: "text" | "decimal";
  ariaLabel: string;
  onCommit: (value: string) => void;
};

/** Text input that saves when it loses focus or on Enter, and restores the saved value on Escape. */
function InlineInput(props: TInlineInputProps) {
  const { value, placeholder, disabled, inputMode = "text", ariaLabel, onCommit } = props;
  const [draft, setDraft] = useState(value);

  useEffect(() => setDraft(value), [value]);

  const commit = () => {
    if (draft.trim() !== value) onCommit(draft.trim());
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") event.currentTarget.blur();
    if (event.key === "Escape") {
      setDraft(value);
      event.currentTarget.blur();
    }
  };

  return (
    <input
      value={draft}
      inputMode={inputMode}
      placeholder={placeholder}
      aria-label={ariaLabel}
      disabled={disabled}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={commit}
      onKeyDown={handleKeyDown}
      className={textInputClassName}
    />
  );
}

type TCustomFieldValueEditorProps = {
  field: TCustomField;
  value: TCustomFieldValue;
  projectId: string;
  disabled?: boolean;
  onChange: (value: TCustomFieldValue) => void;
};

export const CustomFieldValueEditor = observer(function CustomFieldValueEditor(props: TCustomFieldValueEditorProps) {
  const { field, value, projectId, disabled, onChange } = props;
  const { t } = useTranslation();
  const placeholder = t("custom_fields.empty_value");

  switch (field.field_type) {
    case "text":
      return (
        <InlineInput
          value={typeof value === "string" ? value : ""}
          placeholder={placeholder}
          disabled={disabled}
          ariaLabel={field.name}
          onCommit={(next) => onChange(next || null)}
        />
      );

    case "number":
      return (
        <InlineInput
          value={typeof value === "number" ? String(value) : ""}
          placeholder={placeholder}
          disabled={disabled}
          inputMode="decimal"
          ariaLabel={field.name}
          onCommit={(next) => onChange(next ? next.replace(",", ".") : null)}
        />
      );

    case "date":
      return (
        <DateSelect
          value={typeof value === "string" ? (getDate(value) ?? null) : null}
          onChange={(date) => onChange(date ? (renderFormattedPayloadDate(date) ?? null) : null)}
          placeholder={placeholder}
          disabled={disabled}
          clearable
          variant="select-ghost-md"
        />
      );

    case "single_select": {
      const selected = field.options.find((option) => option.id === value) ?? null;
      return (
        <Select<TCustomFieldOption>
          getValues={() => field.options}
          value={selected}
          onChange={(optionId) => onChange(optionId && optionId !== value ? optionId : null)}
          disabled={disabled}
          placeholder={placeholder}
          getOptionValue={(option) => option.id}
          getOptionLabel={(option) => option.name}
          getOptionIcon={(option) => <OptionDot color={option.color} />}
        >
          <Select.Trigger<TCustomFieldOption>
            disabled={disabled}
            variant="select-ghost-md"
            prependIcon={(options) => (options[0] ? <OptionDot color={options[0].color} /> : undefined)}
            label={(options) => options[0]?.name ?? placeholder}
          >
            {(options) => (
              <span className={cn("min-w-0 grow truncate text-left", { "text-placeholder": !options[0] })}>
                {options[0]?.name ?? placeholder}
              </span>
            )}
          </Select.Trigger>
        </Select>
      );
    }

    case "multi_select": {
      const selectedIds = Array.isArray(value) ? value : [];
      const selected = field.options.filter((option) => selectedIds.includes(option.id));
      return (
        <Select<TCustomFieldOption>
          multiple
          getValues={() => field.options}
          value={selected}
          onChange={(optionIds) => onChange(optionIds.length ? optionIds : null)}
          disabled={disabled}
          placeholder={placeholder}
          getOptionValue={(option) => option.id}
          getOptionLabel={(option) => option.name}
          getOptionIcon={(option) => <OptionDot color={option.color} />}
        >
          <Select.Trigger<TCustomFieldOption>
            disabled={disabled}
            variant="select-ghost-md"
            label={(options) => options.map((option) => option.name).join(", ") || placeholder}
          >
            {(options) =>
              options.length ? (
                <span className="flex min-w-0 grow flex-wrap gap-1">
                  {options.map((option) => (
                    <span key={option.id} className="inline-flex items-center gap-1 truncate">
                      <OptionDot color={option.color} />
                      {option.name}
                    </span>
                  ))}
                </span>
              ) : (
                <span className="min-w-0 grow truncate text-left text-placeholder">{placeholder}</span>
              )
            }
          </Select.Trigger>
        </Select>
      );
    }

    case "people":
      return (
        <MemberSelect
          multiple
          projectId={projectId}
          value={Array.isArray(value) ? value : []}
          onChange={(userIds) => onChange(userIds.length ? userIds : null)}
          disabled={disabled}
          placeholder={placeholder}
          variant="select-ghost-md"
        />
      );

    default:
      return null;
  }
});
