import type { RequestEventType } from "./request-types";

export type UserRole = "admin" | "club_lead" | "finance_approver";

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
}

export type ClubStatus =
  | "drafting"
  | "submitted"
  | "under_review"
  | "changes_requested"
  | "approved"
  | "rejected";

export interface Club {
  id: number;
  name: string;
  description: string;
  status: ClubStatus;
  submitter_id: number;
}

export type ClubSortField = "name" | "owner" | "status" | "updated";
export type SortOrder = "asc" | "desc";

/** A club as the list endpoint returns it, with what the tables show. */
export interface ClubListItem extends Club {
  owner_name: string;
  updated_at: string;
  documents_provided: number;
  documents_total: number;
}

/** One page of GET /clubs. `status_counts` ignores the filters. */
export interface ClubPage {
  items: ClubListItem[];
  total: number;
  status_counts: Record<ClubStatus, number>;
}

export type RequirementType =
  | "constitution"
  | "exec_list"
  | "budget"
  | "advisor_form"
  | "bank_account_setup"
  | "exec_onboarding";

export type RequirementStatus =
  "pending" | "submitted" | "approved" | "rejected";

export interface Requirement {
  id: number;
  club_id: number;
  requirement_type: RequirementType;
  kind: "document" | "checklist";
  status: RequirementStatus;
  link_url: string | null;
  reviewer_note: string | null;
}

export type EventType =
  | "created"
  | "submitted"
  | "review_started"
  | "changes_requested"
  | "resubmitted"
  | "approved"
  | "rejected"
  | "requirement_submitted"
  | "requirement_approved"
  | "requirement_rejected"
  | "comment_posted"
  | "role_changed"
  | RequestEventType;

export interface ClubEvent {
  id: number;
  event_type: EventType;
  requirement_id: number | null;
  link_url: string | null;
  from_status: ClubStatus | null;
  to_status: ClubStatus | null;
  note: string | null;
  actor_name: string;
  created_at: string;
}

/** One message in a club's discussion (GET /clubs/{id}/comments). */
export interface Comment {
  id: number;
  body: string;
  author_name: string;
  author_role: UserRole;
  created_at: string;
}

/** One page of an admin list: `total` ignores limit and offset. */
export interface Page<T> {
  items: T[];
  total: number;
}

export type UserListItem = User & { created_at: string };

/** One row of the admin activity log, across every club. */
export interface ActivityEntry {
  id: number;
  event_type: EventType;
  created_at: string;
  actor_id: number;
  actor_name: string;
  club_id: number | null;
  club_name: string | null;
  subject_user_id: number | null;
  subject_user_name: string | null;
  request_id: number | null;
  request_title: string | null;
  requirement_type: RequirementType | null;
  from_status: ClubStatus | null;
  to_status: ClubStatus | null;
  note: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}
