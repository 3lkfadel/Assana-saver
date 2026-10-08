/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import useSWR from "swr";
// hooks
import { useCustomField } from "@/hooks/store/use-custom-field";

/** Loads a project's custom fields and their values once per project (SWR dedupes the many callers). */
export const useProjectCustomFields = (workspaceSlug: string | undefined, projectId: string | null | undefined) => {
  const { fetchProjectFields, fetchProjectValues, getProjectFields } = useCustomField();
  const key = workspaceSlug && projectId ? `${workspaceSlug}_${projectId}` : null;

  useSWR(
    key ? `PROJECT_CUSTOM_FIELDS_${key}` : null,
    key && workspaceSlug && projectId ? () => fetchProjectFields(workspaceSlug, projectId) : null,
    { revalidateOnFocus: false }
  );
  useSWR(
    key ? `PROJECT_CUSTOM_FIELD_VALUES_${key}` : null,
    key && workspaceSlug && projectId ? () => fetchProjectValues(workspaceSlug, projectId) : null,
    { revalidateOnFocus: false }
  );

  return getProjectFields(projectId) ?? [];
};
