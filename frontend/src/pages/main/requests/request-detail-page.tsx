import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { TableSkeleton } from "@/components/shared/table-skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/contexts";
import { OctagonAlertIcon } from "@/icons";
import { apiFetch } from "@/lib/api";
import { REQUEST_TYPE_LABELS } from "@/lib/request-labels";
import type {
  RequestDetail,
  RequestEvent,
  RequestStatus,
} from "@/lib/request-types";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { ApprovalsCard } from "./approvals-card";
import { RequestActions } from "./request-actions";
import { RequestDetailsCard } from "./request-details-card";
import { RequestHistoryCard } from "./request-history-card";
import { RequestStatusBadge } from "./request-status-badge";

const EDITABLE_STATUSES: readonly RequestStatus[] = [
  "draft",
  "changes_requested",
];

export default function RequestDetailPage() {
  const { requestId } = useParams();
  const { user } = useAuth();

  const request = useQuery({
    queryKey: ["requests", requestId],
    queryFn: () => apiFetch<RequestDetail>(`/requests/${requestId}`),
  });
  const events = useQuery({
    queryKey: ["requests", requestId, "events"],
    queryFn: () => apiFetch<RequestEvent[]>(`/requests/${requestId}/events`),
  });

  const error = request.error ?? events.error;
  if (error) {
    return (
      <Alert variant="destructive" className="p-4">
        <OctagonAlertIcon className="size-5" />
        <AlertTitle>Could not load request</AlertTitle>
        <AlertDescription>{error.message}</AlertDescription>
      </Alert>
    );
  }

  if (!request.data || !events.data) return <RequestDetailSkeleton />;

  const { data } = request;
  const isEditable =
    data.created_by_id === user?.id && EDITABLE_STATUSES.includes(data.status);
  // Finance approvers can't open clubs, so the name isn't a link for them.
  const canOpenClub = user?.role !== "finance_approver";

  return (
    <div>
      <PageMeta
        title={data.title}
        description={`${REQUEST_TYPE_LABELS[data.request_type]} request`}
      />
      <PageBreadcrumb pageTitle={data.title} />

      <div className="space-y-6">
        <Card className="rounded-2xl border border-gray-200 bg-white p-5 sm:p-6 dark:border-gray-800 dark:bg-white/3">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <RequestStatusBadge status={data.status} />
                {data.round > 1 && (
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    Round {data.round}
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-700 dark:text-gray-400">
                {REQUEST_TYPE_LABELS[data.request_type]} request for{" "}
                {canOpenClub ? (
                  <Link
                    to={`/clubs/${data.club_id}`}
                    className="font-medium text-gray-800 hover:text-brand-500 dark:text-white/90 dark:hover:text-brand-400"
                  >
                    {data.club_name}
                  </Link>
                ) : (
                  data.club_name
                )}
              </p>
            </div>
            {isEditable && (
              <Button
                size="sm"
                variant="outline"
                nativeButton={false}
                render={<Link to={`/requests/${data.id}/edit`} />}
              >
                Edit
              </Button>
            )}
          </div>

          <RequestActions request={data} />
        </Card>

        <RequestDetailsCard details={data.details} />

        <ApprovalsCard
          approval_steps={data.approval_steps}
          approvals={data.approvals}
          awaiting_role={data.awaiting_role}
        />

        <RequestHistoryCard events={events.data} />
      </div>
    </div>
  );
}

/** The page's shape while its two requests load. */
function RequestDetailSkeleton() {
  return (
    <div role="status" aria-label="Loading request" className="space-y-6">
      <Skeleton className="h-7 w-48 bg-gray-200 dark:bg-gray-800" />
      <Card className="space-y-3 rounded-2xl border border-gray-200 bg-white p-5 sm:p-6 dark:border-gray-800 dark:bg-white/3">
        <Skeleton className="h-5 w-24 rounded-full bg-gray-200 dark:bg-gray-800" />
        <Skeleton className="h-4 w-3/4 bg-gray-100 dark:bg-gray-800/60" />
      </Card>
      <Card className="overflow-hidden rounded-2xl border border-gray-200 bg-white p-0 sm:p-0 dark:border-gray-800 dark:bg-white/3">
        <TableSkeleton rows={4} />
      </Card>
    </div>
  );
}
