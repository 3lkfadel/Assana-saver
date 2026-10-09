/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import useSWR from "swr";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectGroupLabel,
  SelectItem,
  SelectList,
  SelectTrigger,
} from "@makeplane/propel/components/select";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
// components
import { SettingsBoxedControlItem } from "@/components/settings/boxed-control-item";
// hooks
import { useSteering } from "@/hooks/store/use-steering";

type TProjectEntitySettingProps = {
  workspaceSlug: string;
  projectId: string;
  isAdmin: boolean;
};

/** The entity of the Group that carries the project (cahier des charges §3), picked branch by branch. */
export const ProjectEntitySetting = observer(function ProjectEntitySetting(props: TProjectEntitySettingProps) {
  const { workspaceSlug, projectId, isAdmin } = props;
  const { t } = useTranslation();
  const steering = useSteering();

  useSWR(`STEERING_REFERENTIAL_${workspaceSlug}`, () => steering.fetchReferential(workspaceSlug), {
    revalidateOnFocus: false,
  });
  useSWR(`PROJECT_STEERING_${projectId}`, () => steering.fetchProjectEntity(workspaceSlug, projectId), {
    revalidateOnFocus: false,
  });

  const referential = steering.getReferential(workspaceSlug);
  const entityId = steering.projectEntityMap[projectId] ?? null;
  const canEdit = isAdmin || !!referential?.can_administer;

  const changeEntity = async (nextEntityId: string) => {
    try {
      await steering.setProjectEntity(workspaceSlug, projectId, nextEntityId);
      setToast({ type: "success", title: t("common.success"), message: t("steering.project_entity.saved") });
    } catch {
      setToast({ type: "error", title: t("common.error.label"), message: t("steering.errors.save") });
    }
  };

  const control =
    referential && referential.entities.length > 0 ? (
      <Select<string>
        items={Object.fromEntries(referential.entities.map((entity) => [entity.id, entity.name]))}
        value={entityId}
        onValueChange={(next) => next && changeEntity(next)}
        disabled={!canEdit}
      >
        <SelectTrigger
          size="md"
          placeholder={t("steering.project_entity.placeholder")}
          aria-label={t("steering.project_entity.title")}
        />
        <SelectContent side="bottom" align="end">
          <SelectList>
            {referential.branches.map((branch) => {
              const entities = steering.getBranchEntities(workspaceSlug, branch.id);
              if (entities.length === 0) return null;
              return (
                <SelectGroup key={branch.id}>
                  <SelectGroupLabel>{branch.name}</SelectGroupLabel>
                  {entities.map((entity) => (
                    <SelectItem key={entity.id} value={entity.id} size="md" label={entity.name} />
                  ))}
                </SelectGroup>
              );
            })}
          </SelectList>
        </SelectContent>
      </Select>
    ) : (
      <span className="text-12 text-tertiary">{t("steering.project_entity.no_referential")}</span>
    );

  return (
    <div className="mt-10 rounded-lg border border-subtle bg-layer-2">
      <SettingsBoxedControlItem
        className="border-0"
        title={t("steering.project_entity.title")}
        description={t("steering.project_entity.description")}
        control={control}
      />
    </div>
  );
});
