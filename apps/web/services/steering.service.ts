/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

export type TSteeringBranch = {
  id: string;
  name: string;
  sort_order: number;
};

export type TSteeringEntity = {
  id: string;
  name: string;
  branch_id: string;
  sort_order: number;
};

export type TSteeringCategory = {
  id: string;
  name: string;
  sort_order: number;
};

export type TSteeringProfileRole = "ceo" | "cabinet" | "branch_director" | "entity_manager";

export const STEERING_PROFILE_ROLES: TSteeringProfileRole[] = ["ceo", "cabinet", "branch_director", "entity_manager"];

export type TSteeringProfile = {
  id: string;
  member_id: string;
  role: TSteeringProfileRole;
  branch_id: string | null;
  entity_id: string | null;
};

export type TSteeringReferential = {
  branches: TSteeringBranch[];
  entities: TSteeringEntity[];
  categories: TSteeringCategory[];
  can_administer: boolean;
  my_profiles: TSteeringProfile[];
};

export type TSteeringProfilePayload = {
  member_id: string;
  role: TSteeringProfileRole;
  branch_id?: string;
  entity_id?: string;
};

export type TSteeringStatus = "to_start" | "in_progress" | "in_validation" | "waiting" | "done" | "cancelled";

export const STEERING_STATUSES: TSteeringStatus[] = [
  "to_start",
  "in_progress",
  "in_validation",
  "waiting",
  "done",
  "cancelled",
];

export type TSteeringWaitingFor = "internal" | "client_partner" | "regulatory";

export const STEERING_WAITING_FOR: TSteeringWaitingFor[] = ["internal", "client_partner", "regulatory"];

export type TSteeringRiskNature =
  | "financial"
  | "regulatory"
  | "legal"
  | "schedule"
  | "reputation"
  | "governance"
  | "hr"
  | "operational";

export const STEERING_RISK_NATURES: TSteeringRiskNature[] = [
  "financial",
  "regulatory",
  "legal",
  "schedule",
  "reputation",
  "governance",
  "hr",
  "operational",
];

/** Required §4 fields the work item does not carry yet. */
export type TSteeringMissingField =
  | "entity"
  | "category"
  | "assignee"
  | "supervisor"
  | "approver"
  | "priority"
  | "target_date"
  | "waiting_for"
  | "closure";

export type TIssueSteering = {
  issue_id: string;
  /** null: carried by the project's entity. */
  entity_id: string | null;
  project_entity_id: string | null;
  category_id: string | null;
  supervisor_id: string | null;
  approver_id: string | null;
  status: TSteeringStatus;
  progress: number;
  waiting_for: TSteeringWaitingFor | null;
  waiting_since: string | null;
  risk_nature: TSteeringRiskNature | null;
  risk_effective_date: string | null;
  risk_description: string;
  closure_date: string | null;
  closure_comment: string;
  situation: string;
  situation_updated_at: string | null;
  updated_at: string | null;
  missing: TSteeringMissingField[];
};

export type TIssueSteeringPayload = Partial<
  Pick<
    TIssueSteering,
    | "entity_id"
    | "category_id"
    | "supervisor_id"
    | "approver_id"
    | "status"
    | "progress"
    | "waiting_for"
    | "risk_nature"
    | "risk_effective_date"
    | "risk_description"
    | "closure_date"
    | "closure_comment"
    | "situation"
  >
>;

export class SteeringService extends APIService {
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

  private url(workspaceSlug: string, suffix = ""): string {
    return `/api/workspaces/${workspaceSlug}/steering/${suffix}`;
  }

  getReferential(workspaceSlug: string): Promise<TSteeringReferential> {
    return this.unwrap(this.get(this.url(workspaceSlug)));
  }

  bootstrap(workspaceSlug: string): Promise<TSteeringReferential> {
    return this.unwrap(this.post(this.url(workspaceSlug, "bootstrap/")));
  }

  createBranch(workspaceSlug: string, name: string): Promise<TSteeringBranch> {
    return this.unwrap(this.post(this.url(workspaceSlug, "branches/"), { name }));
  }

  updateBranch(workspaceSlug: string, branchId: string, data: Partial<TSteeringBranch>): Promise<TSteeringBranch> {
    return this.unwrap(this.patch(this.url(workspaceSlug, `branches/${branchId}/`), data));
  }

  deleteBranch(workspaceSlug: string, branchId: string): Promise<void> {
    return this.unwrap(this.delete(this.url(workspaceSlug, `branches/${branchId}/`)));
  }

  createEntity(workspaceSlug: string, data: { name: string; branch_id: string }): Promise<TSteeringEntity> {
    return this.unwrap(this.post(this.url(workspaceSlug, "entities/"), data));
  }

  updateEntity(workspaceSlug: string, entityId: string, data: Partial<TSteeringEntity>): Promise<TSteeringEntity> {
    return this.unwrap(this.patch(this.url(workspaceSlug, `entities/${entityId}/`), data));
  }

  deleteEntity(workspaceSlug: string, entityId: string): Promise<void> {
    return this.unwrap(this.delete(this.url(workspaceSlug, `entities/${entityId}/`)));
  }

  createCategory(workspaceSlug: string, name: string): Promise<TSteeringCategory> {
    return this.unwrap(this.post(this.url(workspaceSlug, "categories/"), { name }));
  }

  updateCategory(workspaceSlug: string, categoryId: string, name: string): Promise<TSteeringCategory> {
    return this.unwrap(this.patch(this.url(workspaceSlug, `categories/${categoryId}/`), { name }));
  }

  deleteCategory(workspaceSlug: string, categoryId: string): Promise<void> {
    return this.unwrap(this.delete(this.url(workspaceSlug, `categories/${categoryId}/`)));
  }

  listProfiles(workspaceSlug: string): Promise<TSteeringProfile[]> {
    return this.unwrap(this.get(this.url(workspaceSlug, "profiles/")));
  }

  createProfile(workspaceSlug: string, data: TSteeringProfilePayload): Promise<TSteeringProfile> {
    return this.unwrap(this.post(this.url(workspaceSlug, "profiles/"), data));
  }

  deleteProfile(workspaceSlug: string, profileId: string): Promise<void> {
    return this.unwrap(this.delete(this.url(workspaceSlug, `profiles/${profileId}/`)));
  }

  getProjectEntity(workspaceSlug: string, projectId: string): Promise<{ entity_id: string | null }> {
    return this.unwrap(this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/steering/`));
  }

  setProjectEntity(workspaceSlug: string, projectId: string, entityId: string): Promise<{ entity_id: string }> {
    return this.unwrap(
      this.put(`/api/workspaces/${workspaceSlug}/projects/${projectId}/steering/`, { entity_id: entityId })
    );
  }

  getIssueSteering(workspaceSlug: string, projectId: string, issueId: string): Promise<TIssueSteering> {
    return this.unwrap(this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/steering/`));
  }

  updateIssueSteering(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    data: TIssueSteeringPayload
  ): Promise<TIssueSteering> {
    return this.unwrap(
      this.patch(`/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/steering/`, data)
    );
  }
}
