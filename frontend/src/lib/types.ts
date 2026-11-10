export type UserRole = "admin" | "club_lead";

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

export interface ClubEvent {
  id: number;
  event_type: string;
  requirement_id: number | null;
  link_url: string | null;
  from_status: ClubStatus | null;
  to_status: ClubStatus;
  note: string | null;
  actor_name: string;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}
