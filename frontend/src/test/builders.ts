import type {
  Club,
  ClubEvent,
  Requirement,
  RequirementType,
  User,
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
