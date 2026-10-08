/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useState } from "react";
import type { FormEvent } from "react";
import { observer } from "mobx-react";
import { v4 as uuidv4 } from "uuid";
import { Button } from "@makeplane/propel/components/button";
import { Icon } from "@makeplane/propel/components/icon";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { Select, SelectContent, SelectItem, SelectList, SelectTrigger } from "@makeplane/propel/components/select";
import { AddOutline, CloseOutline } from "@makeplane/propel/icons";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
// hooks
import { useCustomField } from "@/hooks/store/use-custom-field";
// types
import type { TCustomField, TCustomFieldType } from "@/services/custom-field.service";
import { CUSTOM_FIELD_TYPES } from "@/services/custom-field.service";

const OPTION_COLORS = ["#16a34a", "#f97316", "#8b5cf6", "#3f76ff", "#14b8a6", "#ea580c", "#ec4899", "#64748b"];

/** `key` identifies the row while editing; `id` is the saved option id, absent for new options. */
type TOptionDraft = { key: string; id?: string; name: string; color: string };

type TCustomFieldFormProps = {
  workspaceSlug: string;
  /** The field being edited; omitted when creating one. */
  field?: TCustomField;
  onSaved: (field: TCustomField) => void | Promise<void>;
  onCancel: () => void;
};

export const CustomFieldForm = observer(function CustomFieldForm(props: TCustomFieldFormProps) {
  const { workspaceSlug, field, onSaved, onCancel } = props;
  const { t } = useTranslation();
  const { createField, updateField } = useCustomField();
  // states
  const [name, setName] = useState(field?.name ?? "");
  const [fieldType, setFieldType] = useState<TCustomFieldType>(field?.field_type ?? "single_select");
  const [precision, setPrecision] = useState(field?.number_precision ?? 0);
  const [options, setOptions] = useState<TOptionDraft[]>(
    field?.options.map(({ id, name: optionName, color }) => ({ key: id, id, name: optionName, color })) ?? [
      { key: uuidv4(), name: "", color: OPTION_COLORS[0] },
    ]
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const focusOnMount = useCallback((element: HTMLInputElement | null) => element?.focus(), []);

  const isListType = fieldType === "single_select" || fieldType === "multi_select";

  const updateOption = (index: number, update: Partial<TOptionDraft>) =>
    setOptions((current) => current.map((option, i) => (i === index ? { ...option, ...update } : option)));

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedName = name.trim();
    const cleanOptions = options
      .map(({ id, name: optionName, color }) => ({ id, name: optionName.trim(), color }))
      .filter((option) => option.name);
    if (!trimmedName) {
      setToast({ type: "error", title: t("common.error.label"), message: t("custom_fields.errors.name_required") });
      return;
    }
    if (isListType && cleanOptions.length === 0) {
      setToast({ type: "error", title: t("common.error.label"), message: t("custom_fields.errors.options_required") });
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        name: trimmedName,
        number_precision: precision,
        ...(isListType && { options: cleanOptions }),
      };
      const saved = field
        ? await updateField(workspaceSlug, field.id, payload)
        : await createField(workspaceSlug, { ...payload, field_type: fieldType });
      await onSaved(saved);
    } catch (error) {
      const message = (error as { error?: string } | undefined)?.error;
      setToast({
        type: "error",
        title: t("common.error.label"),
        message: message?.includes("already exists")
          ? t("custom_fields.errors.duplicate")
          : t("custom_fields.errors.save"),
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4 rounded-md border border-subtle bg-surface-1 p-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-12 text-secondary">
          {t("custom_fields.name")}
          <InputGroup size="md">
            <Input size="md" ref={focusOnMount} value={name} onChange={(event) => setName(event.target.value)} />
          </InputGroup>
        </label>
        <div className="flex flex-col gap-1 text-12 text-secondary">
          {t("custom_fields.type")}
          <Select<TCustomFieldType>
            value={fieldType}
            onValueChange={(next) => next && setFieldType(next)}
            disabled={!!field}
          >
            <SelectTrigger size="md" aria-label={t("custom_fields.type")} />
            <SelectContent side="bottom" align="start">
              <SelectList>
                {CUSTOM_FIELD_TYPES.map((type) => (
                  <SelectItem key={type} value={type} size="md" label={t(`custom_fields.types.${type}`)} />
                ))}
              </SelectList>
            </SelectContent>
          </Select>
        </div>
      </div>

      {fieldType === "number" && (
        <label className="flex w-40 flex-col gap-1 text-12 text-secondary">
          {t("custom_fields.precision")}
          <InputGroup size="md">
            <Input
              size="md"
              type="number"
              min={0}
              max={6}
              value={precision}
              onChange={(event) => setPrecision(Math.max(0, Math.min(6, Number(event.target.value) || 0)))}
            />
          </InputGroup>
        </label>
      )}

      {isListType && (
        <div className="flex flex-col gap-2">
          <span className="text-12 text-secondary">{t("custom_fields.options")}</span>
          {options.map((option, index) => (
            <div key={option.key} className="flex items-center gap-2">
              <input
                type="color"
                value={option.color || OPTION_COLORS[0]}
                onChange={(event) => updateOption(index, { color: event.target.value })}
                aria-label={t("custom_fields.option_color")}
                className="size-7 shrink-0 cursor-pointer rounded-sm border border-subtle bg-transparent"
              />
              <div className="grow">
                <InputGroup size="md">
                  <Input
                    size="md"
                    value={option.name}
                    placeholder={t("custom_fields.option_placeholder")}
                    onChange={(event) => updateOption(index, { name: event.target.value })}
                  />
                </InputGroup>
              </div>
              <IconButton
                variant="ghost"
                size="sm"
                icon={<Icon icon={CloseOutline} />}
                aria-label={t("custom_fields.remove_option")}
                onClick={() => setOptions((current) => current.filter((_, i) => i !== index))}
              />
            </div>
          ))}
          <div>
            <Button
              variant="ghost"
              size="sm"
              stretch="auto"
              icon={<Icon icon={AddOutline} />}
              label={t("custom_fields.add_option")}
              onClick={() =>
                setOptions((current) => [
                  ...current,
                  { key: uuidv4(), name: "", color: OPTION_COLORS[current.length % OPTION_COLORS.length] },
                ])
              }
            />
          </div>
        </div>
      )}

      <div className="flex items-center justify-end gap-2">
        <Button variant="secondary" size="sm" stretch="auto" onClick={onCancel} label={t("common.cancel")} />
        <Button
          type="submit"
          variant="primary"
          size="sm"
          stretch="auto"
          disabled={isSubmitting}
          label={isSubmitting ? t("common.saving") : t("custom_fields.save")}
        />
      </div>
    </form>
  );
});
