/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
import { Button } from "@makeplane/propel/components/button";
import { Icon } from "@makeplane/propel/components/icon";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { Menu, MenuContent, MenuItem, MenuTrigger } from "@makeplane/propel/components/menu";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { AddOutline, CloseOutline, DeleteOutline, EditOutline } from "@makeplane/propel/icons";
import { EUserPermissionsLevel } from "@plane/constants";
import { ConfirmDialog } from "@plane/blocks/dialog";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import { EUserWorkspaceRoles } from "@plane/types";
// hooks
import { useCustomField } from "@/hooks/store/use-custom-field";
import { useUserPermissions } from "@/hooks/store/user";
// types
import type { TCustomField } from "@/services/custom-field.service";
// local imports
import { useProjectCustomFields } from "../use-project-custom-fields";
import { CUSTOM_FIELD_TYPE_ICONS, OptionDot } from "../value-editor";
import { CustomFieldForm } from "./field-form";

type TProjectCustomFieldsSettingsProps = {
  workspaceSlug: string;
  projectId: string;
};

export const ProjectCustomFieldsSettings = observer(function ProjectCustomFieldsSettings(
  props: TProjectCustomFieldsSettingsProps
) {
  const { workspaceSlug, projectId } = props;
  const { t } = useTranslation();
  const { fetchWorkspaceFields, getWorkspaceFields, addFieldToProject, removeFieldFromProject, deleteField } =
    useCustomField();
  const { allowPermissions } = useUserPermissions();
  const projectFields = useProjectCustomFields(workspaceSlug, projectId);
  // states
  const [formFieldId, setFormFieldId] = useState<string | "new" | undefined>(undefined);
  const [fieldToDelete, setFieldToDelete] = useState<TCustomField | undefined>(undefined);
  const [isDeleting, setIsDeleting] = useState(false);

  useSWR(`WORKSPACE_CUSTOM_FIELDS_${workspaceSlug}`, () => fetchWorkspaceFields(workspaceSlug), {
    revalidateOnFocus: false,
  });

  const isWorkspaceAdmin = allowPermissions([EUserWorkspaceRoles.ADMIN], EUserPermissionsLevel.WORKSPACE);
  const projectFieldIds = new Set(projectFields.map((field) => field.id));
  const libraryFields = (getWorkspaceFields(workspaceSlug) ?? []).filter((field) => !projectFieldIds.has(field.id));

  const notifyError = () =>
    setToast({ type: "error", title: t("common.error.label"), message: t("custom_fields.errors.save") });

  const addToProject = async (fieldId: string) => {
    try {
      await addFieldToProject(workspaceSlug, projectId, fieldId);
      setToast({ type: "success", title: t("common.success"), message: t("custom_fields.toasts.added") });
    } catch {
      notifyError();
    }
  };

  const removeFromProject = async (fieldId: string) => {
    try {
      await removeFieldFromProject(workspaceSlug, projectId, fieldId);
      setToast({ type: "success", title: t("common.success"), message: t("custom_fields.toasts.removed") });
    } catch {
      notifyError();
    }
  };

  const confirmDelete = async () => {
    if (!fieldToDelete) return;
    setIsDeleting(true);
    try {
      await deleteField(workspaceSlug, fieldToDelete.id);
      setToast({ type: "success", title: t("common.success"), message: t("custom_fields.toasts.deleted") });
      setFieldToDelete(undefined);
    } catch {
      notifyError();
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <p className="text-13 text-secondary">{t("custom_fields.description")}</p>
        <Menu>
          <MenuTrigger
            render={
              <Button
                variant="primary"
                size="md"
                stretch="auto"
                icon={<Icon icon={AddOutline} />}
                label={t("custom_fields.add")}
              />
            }
          />
          <MenuContent side="bottom" align="end">
            {libraryFields.map((field) => (
              <MenuItem key={field.id} label={field.name} onClick={() => addToProject(field.id)} />
            ))}
            <MenuItem label={t("custom_fields.create")} onClick={() => setFormFieldId("new")} />
          </MenuContent>
        </Menu>
      </div>

      {formFieldId === "new" && (
        <CustomFieldForm
          workspaceSlug={workspaceSlug}
          onCancel={() => setFormFieldId(undefined)}
          onSaved={async (field) => {
            setFormFieldId(undefined);
            await addToProject(field.id);
          }}
        />
      )}

      {projectFields.length === 0 && formFieldId !== "new" && (
        <div className="rounded-md border border-dashed border-subtle px-4 py-8 text-center text-13 text-tertiary">
          {t("custom_fields.empty")}
        </div>
      )}

      <div className="flex flex-col gap-2">
        {projectFields.map((field) => {
          if (formFieldId === field.id)
            return (
              <CustomFieldForm
                key={field.id}
                workspaceSlug={workspaceSlug}
                field={field}
                onCancel={() => setFormFieldId(undefined)}
                onSaved={() => {
                  setFormFieldId(undefined);
                  setToast({ type: "success", title: t("common.success"), message: t("custom_fields.toasts.saved") });
                }}
              />
            );
          const TypeIcon = CUSTOM_FIELD_TYPE_ICONS[field.field_type];
          return (
            <div
              key={field.id}
              className="flex items-center gap-3 rounded-md border border-subtle bg-surface-1 px-4 py-3"
            >
              <TypeIcon className="size-4 shrink-0 text-tertiary" />
              <div className="flex min-w-0 grow flex-col gap-1">
                <span className="text-13 font-medium text-primary">{field.name}</span>
                <div className="flex flex-wrap items-center gap-2 text-12 text-tertiary">
                  <span>{t(`custom_fields.types.${field.field_type}`)}</span>
                  {field.options.map((option) => (
                    <span key={option.id} className="inline-flex items-center gap-1">
                      <OptionDot color={option.color} />
                      {option.name}
                    </span>
                  ))}
                </div>
              </div>
              <Tooltip label={t("custom_fields.edit")}>
                <IconButton
                  variant="ghost"
                  size="sm"
                  icon={<Icon icon={EditOutline} />}
                  aria-label={t("custom_fields.edit")}
                  onClick={() => setFormFieldId(field.id)}
                />
              </Tooltip>
              <Tooltip label={t("custom_fields.remove_from_project")}>
                <IconButton
                  variant="ghost"
                  size="sm"
                  icon={<Icon icon={CloseOutline} />}
                  aria-label={t("custom_fields.remove_from_project")}
                  onClick={() => removeFromProject(field.id)}
                />
              </Tooltip>
              {isWorkspaceAdmin && (
                <Tooltip label={t("custom_fields.delete")}>
                  <IconButton
                    variant="ghost"
                    size="sm"
                    icon={<Icon icon={DeleteOutline} />}
                    aria-label={t("custom_fields.delete")}
                    onClick={() => setFieldToDelete(field)}
                  />
                </Tooltip>
              )}
            </div>
          );
        })}
      </div>

      <ConfirmDialog
        isOpen={!!fieldToDelete}
        handleClose={() => setFieldToDelete(undefined)}
        handleSubmit={confirmDelete}
        isSubmitting={isDeleting}
        title={t("custom_fields.delete")}
        content={t("custom_fields.delete_confirm", { name: fieldToDelete?.name ?? "" })}
      />
    </div>
  );
});
