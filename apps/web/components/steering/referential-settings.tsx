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
import { SwitchHorizontalOutline } from "@makeplane/propel/icons";
import { ConfirmDialog } from "@plane/blocks/dialog";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
// hooks
import { useSteering } from "@/hooks/store/use-steering";
// local imports
import { SteeringNameForm, SteeringNameRow } from "./name-row";
import { SteeringProfilesSettings } from "./profiles-settings";

type TPendingDeletion = { kind: "branch" | "entity" | "category"; id: string; name: string };

/** Reads the API error body (`{ error }`) to tell a duplicate name from any other failure. */
export const isDuplicateNameError = (error: unknown) =>
  typeof error === "object" &&
  error !== null &&
  "error" in error &&
  typeof error.error === "string" &&
  error.error.includes("already");

function SectionTitle(props: { title: string; description?: string }) {
  return (
    <div className="flex flex-col gap-1">
      <h3 className="text-14 font-semibold text-primary">{props.title}</h3>
      {props.description && <p className="text-13 text-secondary">{props.description}</p>}
    </div>
  );
}

export const SteeringReferentialSettings = observer(function SteeringReferentialSettings(props: {
  workspaceSlug: string;
}) {
  const { workspaceSlug } = props;
  const { t } = useTranslation();
  const steering = useSteering();
  // states
  const [pendingDeletion, setPendingDeletion] = useState<TPendingDeletion | undefined>(undefined);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isBootstrapping, setIsBootstrapping] = useState(false);

  useSWR(`STEERING_REFERENTIAL_${workspaceSlug}`, () => steering.fetchReferential(workspaceSlug), {
    revalidateOnFocus: false,
  });

  const referential = steering.getReferential(workspaceSlug);
  if (!referential) return <div className="text-13 text-tertiary">{t("common.loading")}</div>;

  const canEdit = referential.can_administer;

  const showError = (message: string) => setToast({ type: "error", title: t("common.error.label"), message });

  /** Runs a change; returns whether it was saved so forms know when to clear. */
  const save = async (change: () => Promise<void>) => {
    try {
      await change();
      return true;
    } catch (error) {
      showError(isDuplicateNameError(error) ? t("steering.errors.duplicate") : t("steering.errors.save"));
      return false;
    }
  };

  const requestBranchDeletion = (branchId: string, name: string) => {
    if (steering.getBranchEntities(workspaceSlug, branchId).length > 0) {
      showError(t("steering.errors.branch_not_empty"));
      return;
    }
    setPendingDeletion({ kind: "branch", id: branchId, name });
  };

  const confirmDeletion = async () => {
    if (!pendingDeletion) return;
    setIsDeleting(true);
    try {
      if (pendingDeletion.kind === "branch") await steering.deleteBranch(workspaceSlug, pendingDeletion.id);
      if (pendingDeletion.kind === "entity") await steering.deleteEntity(workspaceSlug, pendingDeletion.id);
      if (pendingDeletion.kind === "category") await steering.deleteCategory(workspaceSlug, pendingDeletion.id);
      setPendingDeletion(undefined);
    } catch {
      showError(pendingDeletion.kind === "entity" ? t("steering.errors.entity_in_use") : t("steering.errors.save"));
    } finally {
      setIsDeleting(false);
    }
  };

  const bootstrap = async () => {
    setIsBootstrapping(true);
    try {
      await steering.bootstrap(workspaceSlug);
      setToast({ type: "success", title: t("common.success"), message: t("steering.referential.bootstrapped") });
    } catch {
      showError(t("steering.errors.save"));
    } finally {
      setIsBootstrapping(false);
    }
  };

  return (
    <div className="flex flex-col gap-8">
      {!canEdit && (
        <p className="rounded-md bg-layer-1 px-4 py-3 text-13 text-secondary">{t("steering.referential.read_only")}</p>
      )}

      <section className="flex flex-col gap-4">
        <SectionTitle title={t("steering.branches.title")} description={t("steering.branches.description")} />

        {referential.branches.length === 0 && (
          <div className="flex flex-col items-center gap-3 rounded-md border border-dashed border-subtle px-4 py-8 text-center">
            <p className="text-13 text-tertiary">{t("steering.referential.empty")}</p>
            {canEdit && (
              <>
                <Button
                  variant="primary"
                  size="md"
                  stretch="auto"
                  label={t("steering.referential.bootstrap")}
                  loading={isBootstrapping}
                  onClick={bootstrap}
                />
                <p className="max-w-md text-12 text-tertiary">{t("steering.referential.bootstrap_hint")}</p>
              </>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {referential.branches.map((branch) => {
            const entities = steering.getBranchEntities(workspaceSlug, branch.id);
            return (
              <div key={branch.id} className="flex flex-col gap-1 rounded-md border border-subtle bg-surface-1 p-3">
                <SteeringNameRow
                  name={branch.name}
                  nameClassName="font-semibold"
                  canEdit={canEdit}
                  onRename={(name) => save(() => steering.updateBranch(workspaceSlug, branch.id, { name }))}
                  onDelete={() => requestBranchDeletion(branch.id, branch.name)}
                >
                  <span className="shrink-0 text-12 text-tertiary">
                    {t("steering.branches.entity_count", { count: entities.length })}
                  </span>
                </SteeringNameRow>
                <div className="flex flex-col border-l border-subtle pl-3">
                  {entities.map((entity) => (
                    <SteeringNameRow
                      key={entity.id}
                      name={entity.name}
                      canEdit={canEdit}
                      onRename={(name) => save(() => steering.updateEntity(workspaceSlug, entity.id, { name }))}
                      onDelete={() => setPendingDeletion({ kind: "entity", id: entity.id, name: entity.name })}
                      actions={
                        referential.branches.length > 1 && (
                          <Menu>
                            <MenuTrigger
                              render={
                                <IconButton
                                  variant="ghost"
                                  size="sm"
                                  icon={<Icon icon={SwitchHorizontalOutline} />}
                                  aria-label={`${t("steering.entities.move")} ${entity.name}`}
                                />
                              }
                            />
                            <MenuContent side="bottom" align="end">
                              {referential.branches
                                .filter((target) => target.id !== entity.branch_id)
                                .map((target) => (
                                  <MenuItem
                                    key={target.id}
                                    label={target.name}
                                    onClick={() =>
                                      save(() =>
                                        steering.updateEntity(workspaceSlug, entity.id, { branch_id: target.id })
                                      )
                                    }
                                  />
                                ))}
                            </MenuContent>
                          </Menu>
                        )
                      }
                    />
                  ))}
                  {canEdit && (
                    <div className="pt-1">
                      <SteeringNameForm
                        placeholder={t("steering.entities.placeholder")}
                        submitLabel={t("common.add")}
                        onSubmit={(name) => save(() => steering.createEntity(workspaceSlug, branch.id, name))}
                      />
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {canEdit && (
          <SteeringNameForm
            placeholder={t("steering.branches.placeholder")}
            submitLabel={t("steering.branches.add")}
            onSubmit={(name) => save(() => steering.createBranch(workspaceSlug, name))}
          />
        )}
      </section>

      <section className="flex flex-col gap-3">
        <SectionTitle title={t("steering.categories.title")} description={t("steering.categories.description")} />
        <div className="flex flex-col rounded-md border border-subtle bg-surface-1 px-3 py-2">
          {referential.categories.length === 0 && (
            <p className="py-1 text-13 text-tertiary">{t("steering.categories.empty")}</p>
          )}
          {referential.categories.map((category) => (
            <SteeringNameRow
              key={category.id}
              name={category.name}
              canEdit={canEdit}
              onRename={(name) => save(() => steering.updateCategory(workspaceSlug, category.id, name))}
              onDelete={() => setPendingDeletion({ kind: "category", id: category.id, name: category.name })}
            />
          ))}
        </div>
        {canEdit && (
          <SteeringNameForm
            placeholder={t("steering.categories.placeholder")}
            submitLabel={t("steering.categories.add")}
            onSubmit={(name) => save(() => steering.createCategory(workspaceSlug, name))}
          />
        )}
      </section>

      {canEdit && (
        <section className="flex flex-col gap-3">
          <SectionTitle title={t("steering.profiles.title")} description={t("steering.profiles.description")} />
          <SteeringProfilesSettings workspaceSlug={workspaceSlug} />
        </section>
      )}

      <ConfirmDialog
        isOpen={!!pendingDeletion}
        handleClose={() => setPendingDeletion(undefined)}
        handleSubmit={confirmDeletion}
        isSubmitting={isDeleting}
        title={t("common.delete")}
        content={t("steering.delete_confirm", { name: pendingDeletion?.name ?? "" })}
      />
    </div>
  );
});
