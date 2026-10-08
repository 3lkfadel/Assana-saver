/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
// components
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { PageHead } from "@/components/core/page-title";
import { ProjectCustomFieldsSettings } from "@/components/custom-fields";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";
// local imports
import { CustomFieldsProjectSettingsHeader } from "./header";

function CustomFieldsSettingsPage() {
  const { workspaceSlug, projectId } = useParams();
  const { t } = useTranslation();
  // store hooks
  const { currentProjectDetails } = useProject();
  const { workspaceUserInfo, allowPermissions } = useUserPermissions();

  const pageTitle = currentProjectDetails?.name
    ? `${currentProjectDetails.name} - ${t("custom_fields.title")}`
    : undefined;
  const canPerformProjectMemberActions = allowPermissions(
    [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
    EUserPermissionsLevel.PROJECT
  );

  if (workspaceUserInfo && !canPerformProjectMemberActions) {
    return <NotAuthorizedView section="settings" isProjectView className="h-auto" />;
  }

  return (
    <SettingsContentWrapper header={<CustomFieldsProjectSettingsHeader />}>
      <PageHead title={pageTitle} />
      {workspaceSlug && projectId && (
        <ProjectCustomFieldsSettings workspaceSlug={workspaceSlug.toString()} projectId={projectId.toString()} />
      )}
    </SettingsContentWrapper>
  );
}

export default observer(CustomFieldsSettingsPage);
