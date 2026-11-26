import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useAuth } from "@/contexts";
import { PlusIcon } from "@/icons";
import { isClubStatus } from "@/lib/labels";
import type { ClubPage, ClubStatus } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router";
import { ClubFilters } from "./club-filters";
import { CLUBS_PAGE_SIZE, clubPageQuery, readPage } from "./club-page-query";
import { ClubsTable, type EmptyState, pastLastPage } from "./clubs-table";
import { Pager } from "./pager";
import { StatusSummary } from "./status-summary";

/** A lead's own clubs, or every club for an admin (with filters, search and a
 * summary). The status, search and page live in the URL, so they survive a
 * reload and the back button. */
export default function ClubsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [searchParams, setSearchParams] = useSearchParams();
  const statusParam = searchParams.get("status");
  const status = isClubStatus(statusParam) ? statusParam : null;
  const search = searchParams.get("q") ?? "";
  const page = readPage(searchParams);

  const clubs = useQuery(
    clubPageQuery({
      statuses: status ? [status] : [],
      search,
      sort: "newest",
      page,
    }),
  );

  // A new filter starts again from page 1.
  const showFilters = (filters: {
    status: ClubStatus | null;
    search: string;
  }) => {
    const params = new URLSearchParams();
    if (filters.status) params.set("status", filters.status);
    if (filters.search) params.set("q", filters.search);
    setSearchParams(params);
  };

  const showPage = (nextPage: number) => {
    const params = new URLSearchParams(searchParams);
    params.set("page", String(nextPage));
    setSearchParams(params);
  };

  const emptyState = chooseEmptyState({
    isAdmin,
    isFiltered: status !== null || search !== "",
    data: clubs.data,
    clearFilters: () => showFilters({ status: null, search: "" }),
    firstPage: () => showPage(1),
    refresh: () => void clubs.refetch(),
  });

  return (
    <div>
      <PageMeta
        title="Clubs | Club Setup"
        description="Clubs and their registration status"
      />
      <PageBreadcrumb pageTitle={isAdmin ? "All clubs" : "My clubs"} />

      {isAdmin && clubs.data && (
        <StatusSummary counts={clubs.data.status_counts} />
      )}

      <Card className="w-full gap-0 overflow-hidden rounded-2xl border border-gray-200 bg-white p-0 sm:p-0 dark:border-gray-800 dark:bg-white/3">
        {isAdmin ? (
          <ClubFilters status={status} search={search} onChange={showFilters} />
        ) : (
          <div className="flex justify-end px-4 py-4 sm:px-6">
            <NewClubButton label="New club" />
          </div>
        )}

        <ClubsTable
          clubs={clubs.data?.items}
          isLoading={clubs.isLoading}
          error={clubs.error}
          showOwner={isAdmin}
          timeColumn="last-updated"
          emptyState={emptyState}
        />
        <Pager
          page={page}
          pageSize={CLUBS_PAGE_SIZE}
          total={clubs.data?.total ?? 0}
          onPageChange={showPage}
        />
      </Card>
    </div>
  );
}

function NewClubButton({ label }: { label: string }) {
  return (
    <Button size="sm" nativeButton={false} render={<Link to="/clubs/new" />}>
      <PlusIcon className="size-5" />
      {label}
    </Button>
  );
}

function chooseEmptyState({
  isAdmin,
  isFiltered,
  data,
  clearFilters,
  firstPage,
  refresh,
}: {
  isAdmin: boolean;
  isFiltered: boolean;
  data: ClubPage | undefined;
  clearFilters: () => void;
  firstPage: () => void;
  refresh: () => void;
}): EmptyState {
  if (data && data.total > 0) return pastLastPage(firstPage);
  if (isFiltered) {
    return {
      title: "No clubs match",
      description: "Try another status, or search for a different name.",
      action: <ActionButton label="Clear filters" onClick={clearFilters} />,
    };
  }
  if (isAdmin) {
    return {
      title: "No clubs yet",
      description: "Clubs appear here as soon as club leads create them.",
      action: <ActionButton label="Refresh" onClick={refresh} />,
    };
  }
  return {
    title: "No clubs yet",
    description: "Create your club, then add links to its documents.",
    action: <NewClubButton label="Create your first club" />,
  };
}

function ActionButton({
  label,
  onClick,
}: {
  label: string;
  onClick: () => void;
}) {
  return (
    <Button size="sm" variant="outline" onClick={onClick}>
      {label}
    </Button>
  );
}
