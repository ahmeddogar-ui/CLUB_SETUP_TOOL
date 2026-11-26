import { apiFetch } from "@/lib/api";
import type { ActivityEntry, EventType, Page } from "@/lib/types";
import { isEventType } from "@/lib/labels";
import { keepPreviousData } from "@tanstack/react-query";

export const ACTIVITY_PAGE_SIZE = 20;

/** The filters as the URL holds them: ids as digits, dates as YYYY-MM-DD. */
export interface ActivityFilters {
  actorId: string | null;
  clubId: string | null;
  eventType: EventType | null;
  since: string | null;
  until: string | null;
}

export const NO_FILTERS: ActivityFilters = {
  actorId: null,
  clubId: null,
  eventType: null,
  since: null,
  until: null,
};

const URL_KEYS: Record<keyof ActivityFilters, string> = {
  actorId: "actor_id",
  clubId: "club_id",
  eventType: "event_type",
  since: "since",
  until: "until",
};

const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const ID_PATTERN = /^[1-9]\d*$/;

function readMatching(
  searchParams: URLSearchParams,
  key: string,
  pattern: RegExp,
) {
  const value = searchParams.get(key);
  return value !== null && pattern.test(value) ? value : null;
}

/** The filters from the URL; a malformed value is ignored. */
export function readFilters(searchParams: URLSearchParams): ActivityFilters {
  const eventType = searchParams.get(URL_KEYS.eventType);
  return {
    actorId: readMatching(searchParams, URL_KEYS.actorId, ID_PATTERN),
    clubId: readMatching(searchParams, URL_KEYS.clubId, ID_PATTERN),
    eventType: isEventType(eventType) ? eventType : null,
    since: readMatching(searchParams, URL_KEYS.since, DATE_PATTERN),
    until: readMatching(searchParams, URL_KEYS.until, DATE_PATTERN),
  };
}

/** The URL for these filters, always starting from page 1. */
export function filtersToSearchParams(filters: ActivityFilters) {
  const params = new URLSearchParams();
  for (const [name, key] of Object.entries(URL_KEYS)) {
    const value = filters[name as keyof ActivityFilters];
    if (value) params.set(key, value);
  }
  return params;
}

export function hasActiveFilters(filters: ActivityFilters): boolean {
  return Object.values(filters).some((value) => value !== null);
}

/** The start of a local calendar day, shifted by `days`, as an ISO instant. */
function startOfDay(date: string, days = 0): string {
  const start = new Date(`${date}T00:00:00`);
  start.setDate(start.getDate() + days);
  return start.toISOString();
}

export function activityPageQuery(filters: ActivityFilters, page: number) {
  const params = new URLSearchParams({
    limit: String(ACTIVITY_PAGE_SIZE),
    offset: String((page - 1) * ACTIVITY_PAGE_SIZE),
  });
  if (filters.actorId) params.set("actor_id", filters.actorId);
  if (filters.clubId) params.set("club_id", filters.clubId);
  if (filters.eventType) params.set("event_type", filters.eventType);
  if (filters.since) params.set("since", startOfDay(filters.since));
  // `until` is exclusive, so the chosen last day is included by going one on.
  if (filters.until) params.set("until", startOfDay(filters.until, 1));

  return {
    queryKey: ["activity", { ...filters, page }],
    queryFn: () => apiFetch<Page<ActivityEntry>>(`/activity?${params}`),
    placeholderData: keepPreviousData,
  };
}
