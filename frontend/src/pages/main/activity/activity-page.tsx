import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { Pager } from "@/components/shared/pager";
import { Card } from "@/components/ui/card";
import { readPage } from "@/pages/main/clubs/club-page-query";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router";
import { ActivityFilterBar } from "./activity-filters";
import {
  ACTIVITY_PAGE_SIZE,
  activityPageQuery,
  type ActivityFilters,
  filtersToSearchParams,
  hasActiveFilters,
  NO_FILTERS,
  readFilters,
} from "./activity-query";
import { ActivityTable } from "./activity-table";

/** Everything that happened across all clubs, for admins. The filters and
 * page live in the URL, so they survive a reload and the back button. */
export default function ActivityPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = readFilters(searchParams);
  const page = readPage(searchParams);

  const activity = useQuery(activityPageQuery(filters, page));
  const entries = activity.data?.items;

  // A new filter starts again from page 1.
  const showFilters = (next: ActivityFilters) =>
    setSearchParams(filtersToSearchParams(next));

  const showPage = (nextPage: number) => {
    const params = new URLSearchParams(searchParams);
    params.set("page", String(nextPage));
    setSearchParams(params);
  };

  // The log's rows name the actor and club; until one loads, show the id.
  const actorName = entries?.find(
    (entry) => String(entry.actor_id) === filters.actorId,
  )?.actor_name;
  const clubName = entries?.find(
    (entry) => String(entry.club_id) === filters.clubId,
  )?.club_name;

  const chips = [];
  if (filters.actorId) {
    chips.push({
      label: `By: ${actorName ?? `#${filters.actorId}`}`,
      onRemove: () => showFilters({ ...filters, actorId: null }),
    });
  }
  if (filters.clubId) {
    chips.push({
      label: `Club: ${clubName ?? `#${filters.clubId}`}`,
      onRemove: () => showFilters({ ...filters, clubId: null }),
    });
  }

  return (
    <div>
      <PageMeta
        title="Activity"
        description="Everything that happened across all clubs"
      />
      <PageBreadcrumb pageTitle="Activity" />

      <Card className="w-full gap-0 overflow-hidden rounded-2xl border border-gray-200 bg-white p-0 sm:p-0 dark:border-gray-800 dark:bg-white/3">
        <ActivityFilterBar
          filters={filters}
          onChange={showFilters}
          chips={chips}
          onClear={
            hasActiveFilters(filters) ? () => showFilters(NO_FILTERS) : null
          }
        />
        <ActivityTable
          entries={entries}
          isLoading={activity.isLoading || activity.isPlaceholderData}
          error={activity.error}
          onFilterActor={(actorId) =>
            showFilters({ ...filters, actorId: String(actorId) })
          }
          onFilterClub={(clubId) =>
            showFilters({ ...filters, clubId: String(clubId) })
          }
          onClearFilters={() => showFilters(NO_FILTERS)}
        />
        <Pager
          page={page}
          pageSize={ACTIVITY_PAGE_SIZE}
          total={activity.data?.total ?? 0}
          onPageChange={showPage}
        />
      </Card>
    </div>
  );
}
