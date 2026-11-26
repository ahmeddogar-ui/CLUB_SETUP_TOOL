import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router";
import { CLUBS_PAGE_SIZE, clubPageQuery, readPage } from "./club-page-query";
import { ClubsTable, type EmptyState, pastLastPage } from "./clubs-table";
import { Pager } from "@/components/shared/pager";

export default function ReviewQueuePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = readPage(searchParams);

  const queue = useQuery(
    clubPageQuery({
      statuses: ["submitted", "under_review"],
      search: "",
      sort: { field: "updated", order: "asc" },
      page,
    }),
  );

  const showPage = (nextPage: number) =>
    setSearchParams({ page: String(nextPage) });

  const emptyState: EmptyState =
    queue.data && queue.data.total > 0
      ? pastLastPage(() => showPage(1))
      : {
          title: "Nothing waiting for review",
          description: "Clubs appear here as soon as their leads submit them.",
          action: (
            <Button
              size="sm"
              variant="outline"
              nativeButton={false}
              render={<Link to="/" />}
            >
              View all clubs
            </Button>
          ),
        };

  return (
    <div>
      <PageMeta title="Review queue" description="Clubs waiting for review" />
      <PageBreadcrumb pageTitle="Review queue" />

      <Card className="w-full gap-0 overflow-hidden rounded-2xl border border-gray-200 bg-white p-0 sm:p-0 dark:border-gray-800 dark:bg-white/3">
        <div className="px-4 py-4 sm:px-6">
          <CardTitle className="text-lg font-semibold text-gray-800 dark:text-white/90">
            Waiting for review
          </CardTitle>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Longest waiting first. Waiting time counts from the club's last
            status change.
          </p>
        </div>

        <ClubsTable
          clubs={queue.data?.items}
          isLoading={queue.isLoading || queue.isPlaceholderData}
          error={queue.error}
          showOwner
          timeColumn="waiting"
          emptyState={emptyState}
        />
        <Pager
          page={page}
          pageSize={CLUBS_PAGE_SIZE}
          total={queue.data?.total ?? 0}
          onPageChange={showPage}
        />
      </Card>
    </div>
  );
}
