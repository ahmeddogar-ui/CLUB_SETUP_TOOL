import { apiFetch } from "@/lib/api";
import type { ClubPage, ClubStatus } from "@/lib/types";
import { keepPreviousData } from "@tanstack/react-query";

export const CLUBS_PAGE_SIZE = 20;

export interface ClubListFilters {
  statuses: ClubStatus[];
  search: string;
  sort: "oldest" | "newest";
  /** 1-based, as shown to the user and kept in the URL. */
  page: number;
}

/** The query for one page of GET /clubs; shared by the club list and the
 * review queue so both page, filter and cache the same way. */
export function clubPageQuery(filters: ClubListFilters) {
  const params = new URLSearchParams({
    sort: filters.sort,
    limit: String(CLUBS_PAGE_SIZE),
    offset: String((filters.page - 1) * CLUBS_PAGE_SIZE),
  });
  filters.statuses.forEach((status) => params.append("status", status));
  if (filters.search) params.set("q", filters.search);

  return {
    queryKey: ["clubs", "list", filters],
    queryFn: () => apiFetch<ClubPage>(`/clubs?${params}`),
    // Keep showing the current page while the next one loads.
    placeholderData: keepPreviousData,
  };
}

/** The 1-based page number from the URL; anything invalid is page 1. */
export function readPage(searchParams: URLSearchParams): number {
  const page = Number(searchParams.get("page"));
  return Number.isInteger(page) && page > 1 ? page : 1;
}
