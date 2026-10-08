/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { set } from "lodash-es";
import { action, makeObservable, observable, runInAction } from "mobx";
import { computedFn } from "mobx-utils";
// services
import type {
  TCustomField,
  TCustomFieldPayload,
  TCustomFieldValue,
  TProjectCustomField,
} from "@/services/custom-field.service";
import { CustomFieldService } from "@/services/custom-field.service";

export interface ICustomFieldStore {
  // observables
  fieldMap: Record<string, TCustomField>;
  workspaceFieldIds: Record<string, string[]>;
  projectFieldIds: Record<string, string[]>;
  valueMap: Record<string, Record<string, TCustomFieldValue>>;
  // computed functions
  getWorkspaceFields: (workspaceSlug: string) => TCustomField[] | undefined;
  getProjectFields: (projectId: string | null | undefined) => TCustomField[] | undefined;
  getValue: (issueId: string, fieldId: string) => TCustomFieldValue;
  // actions
  fetchWorkspaceFields: (workspaceSlug: string) => Promise<TCustomField[]>;
  createField: (workspaceSlug: string, data: TCustomFieldPayload) => Promise<TCustomField>;
  updateField: (workspaceSlug: string, fieldId: string, data: TCustomFieldPayload) => Promise<TCustomField>;
  deleteField: (workspaceSlug: string, fieldId: string) => Promise<void>;
  fetchProjectFields: (workspaceSlug: string, projectId: string) => Promise<TProjectCustomField[]>;
  addFieldToProject: (workspaceSlug: string, projectId: string, fieldId: string) => Promise<void>;
  removeFieldFromProject: (workspaceSlug: string, projectId: string, fieldId: string) => Promise<void>;
  fetchProjectValues: (workspaceSlug: string, projectId: string) => Promise<void>;
  setValue: (
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    fieldId: string,
    value: TCustomFieldValue
  ) => Promise<void>;
}

export class CustomFieldStore implements ICustomFieldStore {
  // observables
  fieldMap: Record<string, TCustomField> = {};
  workspaceFieldIds: Record<string, string[]> = {};
  projectFieldIds: Record<string, string[]> = {};
  valueMap: Record<string, Record<string, TCustomFieldValue>> = {};
  // services
  private service = new CustomFieldService();

  constructor() {
    makeObservable(this, {
      fieldMap: observable,
      workspaceFieldIds: observable,
      projectFieldIds: observable,
      valueMap: observable,
      fetchWorkspaceFields: action,
      createField: action,
      updateField: action,
      deleteField: action,
      fetchProjectFields: action,
      addFieldToProject: action,
      removeFieldFromProject: action,
      fetchProjectValues: action,
      setValue: action,
    });
  }

  getWorkspaceFields = computedFn((workspaceSlug: string) =>
    this.workspaceFieldIds[workspaceSlug]?.map((id) => this.fieldMap[id]).filter(Boolean)
  );

  getProjectFields = computedFn((projectId: string | null | undefined) =>
    projectId ? this.projectFieldIds[projectId]?.map((id) => this.fieldMap[id]).filter(Boolean) : undefined
  );

  getValue = computedFn((issueId: string, fieldId: string) => this.valueMap[issueId]?.[fieldId] ?? null);

  private storeField = (field: TCustomField) => {
    set(this.fieldMap, [field.id], field);
  };

  fetchWorkspaceFields = async (workspaceSlug: string) => {
    const fields = await this.service.listWorkspaceFields(workspaceSlug);
    runInAction(() => {
      fields.forEach(this.storeField);
      this.workspaceFieldIds[workspaceSlug] = fields.map((field) => field.id);
    });
    return fields;
  };

  createField = async (workspaceSlug: string, data: TCustomFieldPayload) => {
    const field = await this.service.createField(workspaceSlug, data);
    runInAction(() => {
      this.storeField(field);
      this.workspaceFieldIds[workspaceSlug] = [...(this.workspaceFieldIds[workspaceSlug] ?? []), field.id];
    });
    return field;
  };

  updateField = async (workspaceSlug: string, fieldId: string, data: TCustomFieldPayload) => {
    const field = await this.service.updateField(workspaceSlug, fieldId, data);
    runInAction(() => this.storeField(field));
    return field;
  };

  deleteField = async (workspaceSlug: string, fieldId: string) => {
    await this.service.deleteField(workspaceSlug, fieldId);
    runInAction(() => {
      this.workspaceFieldIds[workspaceSlug] = (this.workspaceFieldIds[workspaceSlug] ?? []).filter(
        (id) => id !== fieldId
      );
      Object.keys(this.projectFieldIds).forEach((projectId) => {
        this.projectFieldIds[projectId] = this.projectFieldIds[projectId].filter((id) => id !== fieldId);
      });
      delete this.fieldMap[fieldId];
    });
  };

  fetchProjectFields = async (workspaceSlug: string, projectId: string) => {
    const projectFields = await this.service.listProjectFields(workspaceSlug, projectId);
    runInAction(() => {
      projectFields.forEach((projectField) => this.storeField(projectField.custom_field));
      this.projectFieldIds[projectId] = projectFields.map((projectField) => projectField.custom_field_id);
    });
    return projectFields;
  };

  addFieldToProject = async (workspaceSlug: string, projectId: string, fieldId: string) => {
    const projectField = await this.service.addFieldToProject(workspaceSlug, projectId, fieldId);
    runInAction(() => {
      this.storeField(projectField.custom_field);
      this.projectFieldIds[projectId] = [...(this.projectFieldIds[projectId] ?? []), fieldId];
    });
  };

  removeFieldFromProject = async (workspaceSlug: string, projectId: string, fieldId: string) => {
    await this.service.removeFieldFromProject(workspaceSlug, projectId, fieldId);
    runInAction(() => {
      this.projectFieldIds[projectId] = (this.projectFieldIds[projectId] ?? []).filter((id) => id !== fieldId);
    });
  };

  fetchProjectValues = async (workspaceSlug: string, projectId: string) => {
    const values = await this.service.listProjectValues(workspaceSlug, projectId);
    runInAction(() => {
      values.forEach((entry) => set(this.valueMap, [entry.issue_id, entry.custom_field_id], entry.value));
    });
  };

  setValue = async (
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    fieldId: string,
    value: TCustomFieldValue
  ) => {
    const previous = this.getValue(issueId, fieldId);
    // optimistic update, reverted if the API rejects the value
    runInAction(() => set(this.valueMap, [issueId, fieldId], value));
    try {
      const saved = await this.service.setValue(workspaceSlug, projectId, issueId, fieldId, value);
      runInAction(() => set(this.valueMap, [issueId, fieldId], saved?.value ?? null));
    } catch (error) {
      runInAction(() => set(this.valueMap, [issueId, fieldId], previous));
      throw error;
    }
  };
}
