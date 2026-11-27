import type {
  ClubStatus,
  EventType,
  RequirementStatus,
  RequirementType,
  UserRole,
} from "./types";

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

/** Every club status, in lifecycle order (tabs and summary cards). */
export const CLUB_STATUSES: readonly ClubStatus[] = [
  "drafting",
  "submitted",
  "under_review",
  "changes_requested",
  "approved",
  "rejected",
];

export function isClubStatus(value: string | null): value is ClubStatus {
  return CLUB_STATUSES.some((status) => status === value);
}

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

export const EVENT_LABELS: Record<EventType, string> = {
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
  comment_posted: "Comment posted",
  role_changed: "Role changed",
};

/** Every event type, in the order the activity filter lists them. */
export const EVENT_TYPES = Object.keys(EVENT_LABELS) as EventType[];

export function isEventType(value: string | null): value is EventType {
  return EVENT_TYPES.some((type) => type === value);
}

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

const MINUTE_SECONDS = 60;
const HOUR_SECONDS = 60 * MINUTE_SECONDS;
const DAY_SECONDS = 24 * HOUR_SECONDS;
const MONTH_SECONDS = 30 * DAY_SECONDS;
const YEAR_SECONDS = 365 * DAY_SECONDS;

const relativeTime = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

function secondsSince(isoTimestamp: string): number {
  return (Date.now() - new Date(isoTimestamp).getTime()) / 1000;
}

/** "just now", "5 minutes ago", "yesterday", "2 days ago", "3 months ago". */
export function formatRelativeTime(isoTimestamp: string): string {
  const seconds = secondsSince(isoTimestamp);
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", YEAR_SECONDS],
    ["month", MONTH_SECONDS],
    ["day", DAY_SECONDS],
    ["hour", HOUR_SECONDS],
    ["minute", MINUTE_SECONDS],
  ];
  for (const [unit, unitSeconds] of units) {
    if (seconds >= unitSeconds) {
      return relativeTime.format(-Math.floor(seconds / unitSeconds), unit);
    }
  }
  return "just now";
}

/** Whole days since a club last changed status: "Less than a day", "3 days". */
export function formatWaiting(isoTimestamp: string): string {
  const days = Math.floor(secondsSince(isoTimestamp) / DAY_SECONDS);
  if (days < 1) return "Less than a day";
  return days === 1 ? "1 day" : `${days} days`;
}

export const USER_ROLE_LABELS: Record<UserRole, string> = {
  club_lead: "Club lead",
  admin: "Admin",
  finance_approver: "Finance approver",
};

/** Every role, in the order the users page lists them. */
export const USER_ROLES = Object.keys(USER_ROLE_LABELS) as UserRole[];
