/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { Button } from "@makeplane/propel/components/button";
import { Icon } from "@makeplane/propel/components/icon";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { AddOutline, DeleteOutline, EditOutline } from "@makeplane/propel/icons";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";

type TNameFormProps = {
  initialName?: string;
  placeholder?: string;
  submitLabel: string;
  /** Resolves once saved; the form clears (add) or closes (rename) only then. */
  onSubmit: (name: string) => Promise<boolean>;
  onCancel?: () => void;
};

/** One-line name form used to add or rename a branch, an entity or a category. */
export function SteeringNameForm(props: TNameFormProps) {
  const { initialName = "", placeholder, submitLabel, onSubmit, onCancel } = props;
  const { t } = useTranslation();
  const [name, setName] = useState(initialName);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const focusOnMount = useCallback((element: HTMLInputElement | null) => element?.focus(), []);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim() || isSubmitting) return;
    setIsSubmitting(true);
    const saved = await onSubmit(name.trim());
    setIsSubmitting(false);
    if (saved && !onCancel) setName("");
  };

  return (
    <form
      className="flex max-w-xl items-center gap-2"
      onSubmit={handleSubmit}
      onKeyDown={(event) => event.key === "Escape" && onCancel?.()}
    >
      <InputGroup size="md">
        <Input
          size="md"
          ref={onCancel ? focusOnMount : undefined}
          value={name}
          placeholder={placeholder}
          aria-label={placeholder ?? submitLabel}
          onChange={(event) => setName(event.target.value)}
        />
      </InputGroup>
      <Button
        type="submit"
        variant={onCancel ? "primary" : "secondary"}
        size="sm"
        stretch="auto"
        icon={onCancel ? undefined : <Icon icon={AddOutline} />}
        label={submitLabel}
        disabled={!name.trim() || isSubmitting}
      />
      {onCancel && <Button variant="ghost" size="sm" stretch="auto" label={t("common.cancel")} onClick={onCancel} />}
    </form>
  );
}

type TNameRowProps = {
  name: string;
  canEdit: boolean;
  onRename: (name: string) => Promise<boolean>;
  onDelete: () => void;
  /** Rendered between the name and the actions (counts…). */
  children?: ReactNode;
  /** Extra administrator actions, shown before rename and delete. */
  actions?: ReactNode;
  className?: string;
  nameClassName?: string;
};

/** A referential item: its name, renamed in place, and its actions for administrators. */
export function SteeringNameRow(props: TNameRowProps) {
  const { name, canEdit, onRename, onDelete, children, actions, className, nameClassName } = props;
  const { t } = useTranslation();
  const [isEditing, setIsEditing] = useState(false);

  if (isEditing)
    return (
      <div className={cn("py-1", className)}>
        <SteeringNameForm
          initialName={name}
          submitLabel={t("steering.save")}
          onCancel={() => setIsEditing(false)}
          onSubmit={async (next) => {
            const saved = next === name || (await onRename(next));
            if (saved) setIsEditing(false);
            return saved;
          }}
        />
      </div>
    );

  return (
    <div className={cn("group flex min-h-8 items-center gap-2", className)}>
      <span className={cn("min-w-0 grow truncate text-13 text-primary", nameClassName)}>{name}</span>
      {children}
      {canEdit && (
        <div className="flex shrink-0 items-center gap-1 opacity-0 group-focus-within:opacity-100 group-hover:opacity-100">
          {actions}
          <Tooltip label={t("steering.rename")}>
            <IconButton
              variant="ghost"
              size="sm"
              icon={<Icon icon={EditOutline} />}
              aria-label={`${t("steering.rename")} ${name}`}
              onClick={() => setIsEditing(true)}
            />
          </Tooltip>
          <Tooltip label={t("common.delete")}>
            <IconButton
              variant="ghost"
              size="sm"
              icon={<Icon icon={DeleteOutline} />}
              aria-label={`${t("common.delete")} ${name}`}
              onClick={onDelete}
            />
          </Tooltip>
        </div>
      )}
    </div>
  );
}
