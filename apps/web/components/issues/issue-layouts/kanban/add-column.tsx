/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useState } from "react";
import type { FormEvent } from "react";
import { observer } from "mobx-react";
import { AddOutline } from "@makeplane/propel/icons";
import { Button } from "@makeplane/propel/components/button";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { Select, SelectContent, SelectItem, SelectList, SelectTrigger } from "@makeplane/propel/components/select";
import { STATE_GROUPS } from "@plane/constants";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import type { TStateGroups } from "@plane/types";
// hooks
import { useProjectState } from "@/hooks/store/use-project-state";

type TKanbanAddColumn = {
  workspaceSlug: string;
  projectId: string;
};

const DEFAULT_COLUMN_GROUP: TStateGroups = "started";

/** Trailing "+ Add column" slot of a board grouped by state. Creates a new project state. */
export const KanbanAddColumn = observer(function KanbanAddColumn(props: TKanbanAddColumn) {
  const { workspaceSlug, projectId } = props;
  // plane hooks
  const { t } = useTranslation();
  // store hooks
  const { createState } = useProjectState();
  // states
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [name, setName] = useState("");
  const [group, setGroup] = useState<TStateGroups>(DEFAULT_COLUMN_GROUP);
  const [isSubmitting, setIsSubmitting] = useState(false);
  // focus the name field as soon as the form opens
  const focusOnMount = useCallback((element: HTMLInputElement | null) => element?.focus(), []);

  const resetForm = () => {
    setIsFormOpen(false);
    setName("");
    setGroup(DEFAULT_COLUMN_GROUP);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName || isSubmitting) return;

    setIsSubmitting(true);
    try {
      // The API appends new states after the existing ones, so the column lands at the end of its category.
      await createState(workspaceSlug, projectId, { name: trimmedName, group, color: STATE_GROUPS[group].color });
      setToast({ type: "success", title: t("common.success"), message: t("issue.layouts.board_columns.created") });
      resetForm();
    } catch (error) {
      const status = (error as { status?: number } | undefined)?.status;
      setToast({
        type: "error",
        title: t("common.error.label"),
        message:
          status === 400
            ? t("issue.layouts.board_columns.already_exists")
            : t("issue.layouts.board_columns.create_error"),
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isFormOpen)
    return (
      <button
        type="button"
        onClick={() => setIsFormOpen(true)}
        className="flex h-9 w-[280px] flex-shrink-0 items-center gap-2 rounded-md px-2 text-13 font-medium text-tertiary transition-colors hover:bg-layer-transparent-hover hover:text-primary"
      >
        <AddOutline width={14} height={14} />
        {t("issue.layouts.board_columns.add_column")}
      </button>
    );

  return (
    <form
      onSubmit={handleSubmit}
      className="flex h-fit w-[280px] flex-shrink-0 flex-col gap-2 rounded-md border border-subtle bg-surface-1 p-3"
    >
      <InputGroup size="md">
        <Input
          size="md"
          ref={focusOnMount}
          value={name}
          onChange={(event) => setName(event.target.value)}
          onKeyDown={(event) => event.key === "Escape" && resetForm()}
          placeholder={t("issue.layouts.board_columns.column_name")}
          aria-label={t("issue.layouts.board_columns.column_name")}
        />
      </InputGroup>
      <Select<TStateGroups>
        items={Object.fromEntries(
          Object.values(STATE_GROUPS).map((stateGroup) => [
            stateGroup.key,
            t(`workspace_projects.state.${stateGroup.key}`),
          ])
        )}
        value={group}
        onValueChange={(next) => next && setGroup(next)}
      >
        <SelectTrigger size="md" aria-label={t("issue.layouts.board_columns.category")} />
        <SelectContent side="bottom" align="start">
          <SelectList>
            {Object.values(STATE_GROUPS).map((stateGroup) => (
              <SelectItem
                key={stateGroup.key}
                value={stateGroup.key}
                size="md"
                label={t(`workspace_projects.state.${stateGroup.key}`)}
              />
            ))}
          </SelectList>
        </SelectContent>
      </Select>
      <div className="flex items-center justify-end gap-2">
        <Button variant="secondary" size="sm" stretch="auto" onClick={resetForm} label={t("common.cancel")} />
        <Button
          type="submit"
          variant="primary"
          size="sm"
          stretch="auto"
          disabled={!name.trim() || isSubmitting}
          label={isSubmitting ? t("common.creating") : t("common.create")}
        />
      </div>
    </form>
  );
});
