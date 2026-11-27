import { apiFetch } from "@/lib/api";
import type { RequestPage } from "@/lib/request-types";
import { keepPreviousData } from "@tanstack/react-query";

export const REQUESTS_PAGE_SIZE = 20;

export interface RequestListFilters {
  clubId?: string;
  awaitingMe?: boolean;
  sort: "oldest" | "newest";
  /** 1-based, as shown to the user and kept in the URL. */
  page: number;
}

/** The query for one page of GET /requests; shared by the club's Requests tab
 * and the review queue so both page and cache the same way. */
export function requestPageQuery(filters: RequestListFilters) {
  const params = new URLSearchParams({
    sort: filters.sort,
    limit: String(REQUESTS_PAGE_SIZE),
    offset: String((filters.page - 1) * REQUESTS_PAGE_SIZE),
  });
  if (filters.clubId) params.set("club_id", filters.clubId);
  if (filters.awaitingMe) params.set("awaiting_me", "true");

  return {
    queryKey: ["requests", "list", filters],
    queryFn: () => apiFetch<RequestPage>(`/requests?${params}`),
    // Keep the previous page's data while the next loads, so the pager stays
    // put; the table shows skeleton rows meanwhile.
    placeholderData: keepPreviousData,
  };
}
