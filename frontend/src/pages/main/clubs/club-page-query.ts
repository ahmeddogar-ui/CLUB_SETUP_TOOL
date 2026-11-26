import { apiFetch } from "@/lib/api";
import type {
  ClubPage,
  ClubSortField,
  ClubStatus,
  SortOrder,
} from "@/lib/types";
import { keepPreviousData } from "@tanstack/react-query";

export const CLUBS_PAGE_SIZE = 20;

export interface ClubSort {
  field: ClubSortField;
  order: SortOrder;
}

export interface ClubListFilters {
  statuses: ClubStatus[];
  search: string;
  sort: ClubSort;
  /** 1-based, as shown to the user and kept in the URL. */
  page: number;
}

/** The query string GET /clubs and GET /clubs/export.csv share. */
export function clubFilterParams(filters: Omit<ClubListFilters, "page">) {
  const params = new URLSearchParams({
    sort: filters.sort.field,
    order: filters.sort.order,
  });
  filters.statuses.forEach((status) => params.append("status", status));
  if (filters.search) params.set("q", filters.search);
  return params;
}

/** The query for one page of GET /clubs; shared by the club list and the
 * review queue so both page, filter and cache the same way. */
export function clubPageQuery(filters: ClubListFilters) {
  const params = clubFilterParams(filters);
  params.set("limit", String(CLUBS_PAGE_SIZE));
  params.set("offset", String((filters.page - 1) * CLUBS_PAGE_SIZE));

  return {
    queryKey: ["clubs", "list", filters],
    queryFn: () => apiFetch<ClubPage>(`/clubs?${params}`),
    // Keep the previous page's data while the next loads, so the pager and
    // counts stay put; the table shows skeleton rows meanwhile.
    placeholderData: keepPreviousData,
  };
}

/** The 1-based page number from the URL; anything invalid is page 1. */
export function readPage(searchParams: URLSearchParams): number {
  const page = Number(searchParams.get("page"));
  return Number.isInteger(page) && page > 1 ? page : 1;
}

const SORT_FIELDS: readonly ClubSortField[] = [
  "name",
  "owner",
  "status",
  "updated",
];

/** The sort from the URL; anything invalid is most recently updated first. */
export function readSort(searchParams: URLSearchParams): ClubSort {
  const field = SORT_FIELDS.find((value) => value === searchParams.get("sort"));
  if (!field) return { field: "updated", order: "desc" };
  return {
    field,
    order: searchParams.get("order") === "desc" ? "desc" : "asc",
  };
}
