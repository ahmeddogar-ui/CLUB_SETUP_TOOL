import type {
  ActivityEntry,
  Club,
  ClubEvent,
  ClubListItem,
  ClubPage,
  Comment,
  Requirement,
  RequirementType,
  User,
  UserListItem,
} from "@/lib/types";

// Shapes mirror the backend's response schemas (app/schemas.py).

export const LEAD: User = {
  id: 1,
  name: "Lena Lead",
  email: "lena@example.com",
  role: "club_lead",
};

export const ADMIN: User = {
  id: 2,
  name: "Ada Admin",
  email: "ada@example.com",
  role: "admin",
};

export function buildClub(overrides: Partial<Club> = {}): Club {
  return {
    id: 10,
    name: "Chess Club",
    description: "We play chess",
    status: "drafting",
    submitter_id: LEAD.id,
    ...overrides,
  };
}

const DAY_MS = 24 * 60 * 60 * 1000;

/** An ISO timestamp `days` before now. */
export function daysAgo(days: number): string {
  return new Date(Date.now() - days * DAY_MS).toISOString();
}

export function buildClubListItem(
  overrides: Partial<ClubListItem> = {},
): ClubListItem {
  return {
    ...buildClub(),
    owner_name: LEAD.name,
    updated_at: daysAgo(2),
    documents_provided: 0,
    documents_total: 4,
    ...overrides,
  };
}

export function buildClubPage(
  items: ClubListItem[],
  overrides: Partial<ClubPage> = {},
): ClubPage {
  return {
    items,
    total: items.length,
    status_counts: {
      drafting: 0,
      submitted: 0,
      under_review: 0,
      changes_requested: 0,
      approved: 0,
      rejected: 0,
    },
    ...overrides,
  };
}

const REQUIREMENT_KINDS: [RequirementType, Requirement["kind"]][] = [
  ["constitution", "document"],
  ["exec_list", "document"],
  ["budget", "document"],
  ["advisor_form", "document"],
  ["bank_account_setup", "checklist"],
  ["exec_onboarding", "checklist"],
];

export function buildRequirements(
  clubId: number,
  overrides: Partial<Requirement> = {},
): Requirement[] {
  return REQUIREMENT_KINDS.map(([requirement_type, kind], index) => ({
    id: clubId * 100 + index,
    club_id: clubId,
    requirement_type,
    kind,
    status: "pending",
    link_url: null,
    reviewer_note: null,
    ...overrides,
  }));
}

export function buildEvent(overrides: Partial<ClubEvent> = {}): ClubEvent {
  return {
    id: 1,
    event_type: "created",
    requirement_id: null,
    link_url: null,
    from_status: null,
    to_status: "drafting",
    note: null,
    actor_name: LEAD.name,
    created_at: "2026-11-01T12:00:00Z",
    ...overrides,
  };
}

export function buildComment(overrides: Partial<Comment> = {}): Comment {
  return {
    id: 1,
    body: "A comment",
    author_name: LEAD.name,
    author_role: "club_lead",
    created_at: "2026-11-01T12:00:00Z",
    ...overrides,
  };
}

export function buildUserListItem(
  overrides: Partial<UserListItem> = {},
): UserListItem {
  return { ...LEAD, created_at: "2026-10-01T09:00:00Z", ...overrides };
}

export function buildActivityEntry(
  overrides: Partial<ActivityEntry> = {},
): ActivityEntry {
  return {
    id: 1,
    event_type: "created",
    created_at: "2026-11-01T12:00:00Z",
    actor_id: LEAD.id,
    actor_name: LEAD.name,
    club_id: 10,
    club_name: "Chess Club",
    subject_user_id: null,
    subject_user_name: null,
    requirement_type: null,
    from_status: null,
    to_status: "drafting",
    note: null,
    ...overrides,
  };
}
