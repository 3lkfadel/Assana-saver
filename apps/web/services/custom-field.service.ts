/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

export type TCustomFieldType = "text" | "number" | "date" | "single_select" | "multi_select" | "people";

export const CUSTOM_FIELD_TYPES: TCustomFieldType[] = [
  "text",
  "number",
  "date",
  "single_select",
  "multi_select",
  "people",
];

export type TCustomFieldOption = {
  id: string;
  name: string;
  color: string;
  sort_order: number;
};

export type TCustomField = {
  id: string;
  name: string;
  description: string;
  field_type: TCustomFieldType;
  number_precision: number;
  options: TCustomFieldOption[];
  workspace_id: string;
};

export type TProjectCustomField = {
  id: string;
  custom_field: TCustomField;
  custom_field_id: string;
  project_id: string;
  sort_order: number;
};

/** text: string · number: number · date: "YYYY-MM-DD" · single_select: option id · multi_select / people: ids */
export type TCustomFieldValue = string | number | string[] | null;

export type TIssueCustomFieldValue = {
  issue_id: string;
  custom_field_id: string;
  value: TCustomFieldValue;
};

export type TCustomFieldPayload = {
  name?: string;
  description?: string;
  field_type?: TCustomFieldType;
  number_precision?: number;
  options?: { id?: string; name: string; color: string }[];
};

export class CustomFieldService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private unwrap<T>(request: Promise<{ data: T }>): Promise<T> {
    return request
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  listWorkspaceFields(workspaceSlug: string): Promise<TCustomField[]> {
    return this.unwrap(this.get(`/api/workspaces/${workspaceSlug}/custom-fields/`));
  }

  createField(workspaceSlug: string, data: TCustomFieldPayload): Promise<TCustomField> {
    return this.unwrap(this.post(`/api/workspaces/${workspaceSlug}/custom-fields/`, data));
  }

  updateField(workspaceSlug: string, fieldId: string, data: TCustomFieldPayload): Promise<TCustomField> {
    return this.unwrap(this.patch(`/api/workspaces/${workspaceSlug}/custom-fields/${fieldId}/`, data));
  }

  deleteField(workspaceSlug: string, fieldId: string): Promise<void> {
    return this.unwrap(this.delete(`/api/workspaces/${workspaceSlug}/custom-fields/${fieldId}/`));
  }

  listProjectFields(workspaceSlug: string, projectId: string): Promise<TProjectCustomField[]> {
    return this.unwrap(this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/custom-fields/`));
  }

  addFieldToProject(workspaceSlug: string, projectId: string, fieldId: string): Promise<TProjectCustomField> {
    return this.unwrap(
      this.post(`/api/workspaces/${workspaceSlug}/projects/${projectId}/custom-fields/`, { custom_field_id: fieldId })
    );
  }

  removeFieldFromProject(workspaceSlug: string, projectId: string, fieldId: string): Promise<void> {
    return this.unwrap(this.delete(`/api/workspaces/${workspaceSlug}/projects/${projectId}/custom-fields/${fieldId}/`));
  }

  listProjectValues(workspaceSlug: string, projectId: string): Promise<TIssueCustomFieldValue[]> {
    return this.unwrap(this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/custom-field-values/`));
  }

  setValue(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    fieldId: string,
    value: TCustomFieldValue
  ): Promise<TIssueCustomFieldValue> {
    return this.unwrap(
      this.put(`/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/custom-fields/${fieldId}/`, {
        value,
      })
    );
  }
}
