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
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { AddOutline, DeleteOutline } from "@makeplane/propel/icons";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useSteering } from "@/hooks/store/use-steering";
// types
import type { TSteeringProfile, TSteeringProfileRole } from "@/services/steering.service";
import { STEERING_PROFILE_ROLES } from "@/services/steering.service";
// local imports
import { SteeringSelect } from "./select";

export const SteeringProfilesSettings = observer(function SteeringProfilesSettings(props: { workspaceSlug: string }) {
  const { workspaceSlug } = props;
  const { t } = useTranslation();
  const steering = useSteering();
  const {
    getUserDetails,
    workspace: { getWorkspaceMemberIds },
  } = useMember();
  // states
  const [memberId, setMemberId] = useState<string | null>(null);
  const [role, setRole] = useState<TSteeringProfileRole | null>(null);
  const [scopeId, setScopeId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useSWR(`STEERING_PROFILES_${workspaceSlug}`, () => steering.fetchProfiles(workspaceSlug), {
    revalidateOnFocus: false,
  });

  const referential = steering.getReferential(workspaceSlug);
  const profiles = steering.profileMap[workspaceSlug] ?? [];

  const memberName = (userId: string) => {
    const user = getUserDetails(userId);
    return user?.display_name || [user?.first_name, user?.last_name].filter(Boolean).join(" ") || "—";
  };
  const memberOptions = getWorkspaceMemberIds(workspaceSlug).map((userId) => ({
    value: userId,
    label: memberName(userId),
  }));
  const roleOptions = STEERING_PROFILE_ROLES.map((value) => ({ value, label: t(`steering.profiles.roles.${value}`) }));
  const scopeOptions =
    role === "branch_director"
      ? (referential?.branches ?? []).map((branch) => ({ value: branch.id, label: branch.name }))
      : role === "entity_manager"
        ? (referential?.entities ?? []).map((entity) => ({ value: entity.id, label: entity.name }))
        : [];
  const needsScope = role === "branch_director" || role === "entity_manager";
  const canSubmit = !!memberId && !!role && (!needsScope || !!scopeId) && !isSubmitting;

  const scopeLabel = (profile: TSteeringProfile) => {
    if (profile.branch_id) return referential?.branches.find((branch) => branch.id === profile.branch_id)?.name;
    if (profile.entity_id) return steering.getEntity(workspaceSlug, profile.entity_id)?.name;
    return t("steering.profiles.whole_group");
  };

  const addProfile = async () => {
    if (!memberId || !role) return;
    setIsSubmitting(true);
    try {
      await steering.createProfile(workspaceSlug, {
        member_id: memberId,
        role,
        ...(role === "branch_director" && scopeId ? { branch_id: scopeId } : {}),
        ...(role === "entity_manager" && scopeId ? { entity_id: scopeId } : {}),
      });
      setMemberId(null);
      setRole(null);
      setScopeId(null);
    } catch {
      setToast({ type: "error", title: t("common.error.label"), message: t("steering.errors.profile") });
    } finally {
      setIsSubmitting(false);
    }
  };

  const removeProfile = async (profileId: string) => {
    try {
      await steering.deleteProfile(workspaceSlug, profileId);
    } catch {
      setToast({ type: "error", title: t("common.error.label"), message: t("steering.errors.save") });
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col rounded-md border border-subtle bg-surface-1">
        {profiles.length === 0 && <p className="px-3 py-3 text-13 text-tertiary">{t("steering.profiles.empty")}</p>}
        {profiles.map((profile) => (
          <div
            key={profile.id}
            className="flex items-center gap-3 border-b border-subtle px-3 py-2 text-13 last:border-b-0"
          >
            <span className="w-1/3 min-w-0 truncate font-medium text-primary">{memberName(profile.member_id)}</span>
            <span className="w-1/3 min-w-0 truncate text-secondary">
              {t(`steering.profiles.roles.${profile.role}`)}
            </span>
            <span className="min-w-0 grow truncate text-tertiary">{scopeLabel(profile)}</span>
            <Tooltip label={t("common.remove")}>
              <IconButton
                variant="ghost"
                size="sm"
                icon={<Icon icon={DeleteOutline} />}
                aria-label={`${t("common.remove")} ${memberName(profile.member_id)}`}
                onClick={() => removeProfile(profile.id)}
              />
            </Tooltip>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <SteeringSelect
          value={memberId}
          options={memberOptions}
          placeholder={t("steering.profiles.member")}
          ariaLabel={t("steering.profiles.member")}
          onChange={setMemberId}
        />
        <SteeringSelect
          value={role}
          options={roleOptions}
          placeholder={t("steering.profiles.role")}
          ariaLabel={t("steering.profiles.role")}
          onChange={(next) => {
            setRole(next);
            setScopeId(null);
          }}
        />
        {needsScope && (
          <SteeringSelect
            value={scopeId}
            options={scopeOptions}
            placeholder={t("steering.profiles.scope")}
            ariaLabel={t("steering.profiles.scope")}
            onChange={setScopeId}
          />
        )}
        <Button
          variant="secondary"
          size="sm"
          stretch="auto"
          icon={<Icon icon={AddOutline} />}
          label={t("steering.profiles.add")}
          disabled={!canSubmit}
          onClick={addProfile}
        />
      </div>
    </div>
  );
});
