import type {
  RequestEventType,
  RequestStatus,
  RequestType,
} from "./request-types";

type BadgeColor = "primary" | "success" | "error" | "warning" | "info" | "gray";

export const REQUEST_TYPE_LABELS: Record<RequestType, string> = {
  funding: "Funding",
  room_booking: "Room booking",
};

export const REQUEST_STATUS_BADGES: Record<
  RequestStatus,
  { label: string; color: BadgeColor }
> = {
  draft: { label: "Draft", color: "gray" },
  submitted: { label: "Submitted", color: "info" },
  in_review: { label: "In review", color: "primary" },
  changes_requested: { label: "Changes requested", color: "warning" },
  approved: { label: "Approved", color: "success" },
  rejected: { label: "Rejected", color: "error" },
  cancelled: { label: "Cancelled", color: "gray" },
};

export const REQUEST_EVENT_LABELS: Record<RequestEventType, string> = {
  request_created: "Request created",
  request_submitted: "Submitted for review",
  request_review_started: "Review started",
  request_step_approved: "Step approved",
  request_approved: "Request approved",
  request_rejected: "Request rejected",
  request_changes_requested: "Changes requested",
  request_cancelled: "Request cancelled",
};

const CENTS_PER_DOLLAR = 100;

const currencyFormat = new Intl.NumberFormat("en-CA", {
  style: "currency",
  currency: "CAD",
});

/** 17550 -> "$175.50". */
export function formatCents(cents: number): string {
  return currencyFormat.format(cents / CENTS_PER_DOLLAR);
}

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: "medium" });
const timeFormat = new Intl.DateTimeFormat(undefined, { timeStyle: "short" });
const dateTimeFormat = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

/** "Nov 30, 2026, 2:00 PM – 4:00 PM", or both full dates across midnight. */
export function formatTimeRange(startsAt: string, endsAt: string): string {
  const starts = new Date(startsAt);
  const ends = new Date(endsAt);
  if (dateFormat.format(starts) !== dateFormat.format(ends)) {
    return `${dateTimeFormat.format(starts)} – ${dateTimeFormat.format(ends)}`;
  }
  return `${dateFormat.format(starts)}, ${timeFormat.format(starts)} – ${timeFormat.format(ends)}`;
}
