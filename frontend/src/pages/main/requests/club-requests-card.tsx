import { Pager } from "@/components/shared/pager";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/contexts";
import type { Club } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router";
import { readPage } from "../clubs/club-page-query";
import { REQUESTS_PAGE_SIZE, requestPageQuery } from "./request-page-query";
import { RequestsTable } from "./requests-table";

/** The club's funding and room booking requests, newest first. */
export function ClubRequestsCard({ club }: { club: Club }) {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const page = readPage(searchParams);

  const requests = useQuery(
    requestPageQuery({
      clubId: String(club.id),
      sort: "newest",
      page,
    }),
  );

  const isLead = club.submitter_id === user?.id;
  const isApproved = club.status === "approved";

  return (
    <Card className="w-full gap-0 overflow-hidden rounded-2xl border border-gray-200 bg-white p-0 sm:p-0 dark:border-gray-800 dark:bg-white/3">
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-6">
        <CardTitle className="text-lg font-semibold text-gray-800 dark:text-white/90">
          Requests
        </CardTitle>
        {isLead && isApproved && (
          <Button
            size="sm"
            nativeButton={false}
            render={<Link to={`/clubs/${club.id}/requests/new`} />}
          >
            New request
          </Button>
        )}
        {isLead && !isApproved && (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Requests open once the club is approved.
          </p>
        )}
      </div>

      <RequestsTable
        requests={requests.data?.items}
        isLoading={requests.isLoading || requests.isPlaceholderData}
        error={requests.error}
        view="club"
        emptyText="No requests yet."
      />
      <Pager
        page={page}
        pageSize={REQUESTS_PAGE_SIZE}
        total={requests.data?.total ?? 0}
        onPageChange={(nextPage) =>
          setSearchParams({ tab: "requests", page: String(nextPage) })
        }
      />
    </Card>
  );
}
