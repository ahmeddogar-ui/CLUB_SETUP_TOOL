import type { ClubStatus, RequirementStatus, RequirementType } from "./types";

type BadgeColor = "primary" | "success" | "error" | "warning" | "info" | "gray";

export const CLUB_STATUS_BADGES: Record<
  ClubStatus,
  { label: string; color: BadgeColor }
> = {
  drafting: { label: "Drafting", color: "gray" },
  submitted: { label: "Submitted", color: "info" },
  under_review: { label: "Under review", color: "primary" },
  changes_requested: { label: "Changes requested", color: "warning" },
  approved: { label: "Approved", color: "success" },
  rejected: { label: "Rejected", color: "error" },
};

export const REQUIREMENT_STATUS_BADGES: Record<
  RequirementStatus,
  { label: string; color: BadgeColor }
> = {
  pending: { label: "Pending", color: "gray" },
  submitted: { label: "Provided", color: "info" },
  approved: { label: "Approved", color: "success" },
  rejected: { label: "Rejected", color: "error" },
};

export const REQUIREMENT_LABELS: Record<RequirementType, string> = {
  constitution: "Constitution",
  exec_list: "Executive list",
  budget: "Budget",
  advisor_form: "Advisor form",
  bank_account_setup: "Bank account setup",
  exec_onboarding: "Executive onboarding",
};

export const EVENT_LABELS: Record<string, string> = {
  created: "Club created",
  submitted: "Submitted for review",
  review_started: "Review started",
  changes_requested: "Changes requested",
  resubmitted: "Resubmitted",
  approved: "Club approved",
  rejected: "Club rejected",
  requirement_submitted: "Document provided",
  requirement_approved: "Requirement approved",
  requirement_rejected: "Requirement rejected",
};

export const EDITABLE_STATUSES: readonly ClubStatus[] = [
  "drafting",
  "changes_requested",
];

export function formatDateTime(isoTimestamp: string): string {
  return new Date(isoTimestamp).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
