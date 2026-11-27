import type { UserRole } from "./types";

// Shapes mirror the backend's request schemas.

export type RequestType = "funding" | "room_booking";

export type RequestStatus =
  | "draft"
  | "submitted"
  | "in_review"
  | "changes_requested"
  | "approved"
  | "rejected"
  | "cancelled";

export type RequestAction =
  | "submit"
  | "start_review"
  | "approve"
  | "reject"
  | "request_changes"
  | "cancel";

export type RequestEventType =
  | "request_created"
  | "request_submitted"
  | "request_review_started"
  | "request_step_approved"
  | "request_approved"
  | "request_rejected"
  | "request_changes_requested"
  | "request_cancelled";

export interface Room {
  id: number;
  name: string;
  building: string;
  capacity: number;
}

export interface LineItem {
  description: string;
  amount_cents: number;
}

export interface FundingDetailsIn {
  request_type: "funding";
  line_items: LineItem[];
}

export interface RoomBookingDetailsIn {
  request_type: "room_booking";
  room_id: number;
  starts_at: string;
  ends_at: string;
}

export interface FundingDetailsOut {
  request_type: "funding";
  line_items: LineItem[];
  total_cents: number;
}

export interface RoomBookingDetailsOut {
  request_type: "room_booking";
  room_id: number;
  room_name: string;
  starts_at: string;
  ends_at: string;
}

/** The body of POST /clubs/{id}/requests and PATCH /requests/{id}. */
export interface RequestInput {
  title: string;
  details: FundingDetailsIn | RoomBookingDetailsIn;
}

export interface RequestListItem {
  id: number;
  club_id: number;
  club_name: string;
  request_type: RequestType;
  title: string;
  status: RequestStatus;
  awaiting_role: UserRole | null;
  created_by_name: string;
  updated_at: string;
  total_cents: number | null;
  room_name: string | null;
  starts_at: string | null;
  ends_at: string | null;
}

/** One page of GET /requests. */
export interface RequestPage {
  items: RequestListItem[];
  total: number;
}

export interface RequestApproval {
  step: number;
  role: UserRole;
  approver_name: string;
  approved_at: string;
  note: string | null;
}

export interface RequestDetail {
  id: number;
  club_id: number;
  club_name: string;
  request_type: RequestType;
  title: string;
  status: RequestStatus;
  round: number;
  awaiting_role: UserRole | null;
  created_by_id: number;
  created_by_name: string;
  created_at: string;
  updated_at: string;
  approval_steps: UserRole[];
  approvals: RequestApproval[];
  details: FundingDetailsOut | RoomBookingDetailsOut;
  /** What the signed-in user may do now; the UI shows exactly these. */
  allowed_actions: RequestAction[];
}

export interface RequestEvent {
  id: number;
  event_type: RequestEventType;
  actor_name: string;
  note: string | null;
  created_at: string;
}
