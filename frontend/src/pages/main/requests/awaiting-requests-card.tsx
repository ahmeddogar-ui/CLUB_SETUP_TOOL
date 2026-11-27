import { Pager } from "@/components/shared/pager";
import { Card, CardTitle } from "@/components/ui/card";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router";
import { readPage } from "../clubs/club-page-query";
import { REQUESTS_PAGE_SIZE, requestPageQuery } from "./request-page-query";
import { RequestsTable } from "./requests-table";

const PAGE_PARAM = "requests_page";

/** Requests waiting for the signed-in approver's role, longest waiting first. */
export function AwaitingRequestsCard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = readPage(searchParams, PAGE_PARAM);

  const requests = useQuery(
    requestPageQuery({ awaitingMe: true, sort: "oldest", page }),
  );

  const showPage = (nextPage: number) => {
    const params = new URLSearchParams(searchParams);
    params.set(PAGE_PARAM, String(nextPage));
    setSearchParams(params);
  };

  return (
    <Card className="w-full gap-0 overflow-hidden rounded-2xl border border-gray-200 bg-white p-0 sm:p-0 dark:border-gray-800 dark:bg-white/3">
      <div className="px-4 py-4 sm:px-6">
        <CardTitle className="text-lg font-semibold text-gray-800 dark:text-white/90">
          Requests awaiting you
        </CardTitle>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Longest waiting first. Waiting time counts from the request's last
          change.
        </p>
      </div>

      <RequestsTable
        requests={requests.data?.items}
        isLoading={requests.isLoading || requests.isPlaceholderData}
        error={requests.error}
        view="review"
        emptyText="No requests are waiting for you."
      />
      <Pager
        page={page}
        pageSize={REQUESTS_PAGE_SIZE}
        total={requests.data?.total ?? 0}
        onPageChange={showPage}
      />
    </Card>
  );
}
