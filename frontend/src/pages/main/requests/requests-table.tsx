import { TableSkeleton } from "@/components/shared/table-skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { OctagonAlertIcon } from "@/icons";
import { formatRelativeTime, formatWaiting } from "@/lib/labels";
import {
  formatCents,
  formatTimeRange,
  REQUEST_TYPE_LABELS,
} from "@/lib/request-labels";
import type { RequestListItem } from "@/lib/request-types";
import { cn } from "@/utils";
import { Link } from "react-router";
import { RequestStatusBadge } from "./request-status-badge";

const HEADER_CELL_CLASS =
  "px-6 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400";
const CELL_CLASS =
  "px-6 py-4 text-start text-sm text-gray-500 dark:text-gray-400";
// Secondary columns give way on small screens.
const WIDE_ONLY = "hidden md:table-cell";

interface RequestsTableProps {
  requests: RequestListItem[] | undefined;
  /** True on the first load and while another page loads. */
  isLoading: boolean;
  error: Error | null;
  /** A club's tab shows each request's status and age; the review queue shows
   * which club it is for, its type and how long it has waited. */
  view: "club" | "review";
  emptyText: string;
}

export function RequestsTable({
  requests,
  isLoading,
  error,
  view,
  emptyText,
}: RequestsTableProps) {
  if (isLoading) return <TableSkeleton label="Loading requests" />;

  if (error) {
    return (
      <Alert variant="destructive" className="m-6 w-auto p-4">
        <OctagonAlertIcon className="size-5" />
        <AlertTitle>Could not load requests</AlertTitle>
        <AlertDescription>{error.message}</AlertDescription>
      </Alert>
    );
  }

  if (!requests || requests.length === 0) {
    return (
      <p className="border-t border-gray-100 px-6 py-10 text-center text-sm text-gray-500 dark:border-gray-800 dark:text-gray-400">
        {emptyText}
      </p>
    );
  }

  const isClubView = view === "club";

  return (
    <div className="max-w-full overflow-x-auto">
      <Table>
        <TableHeader className="border-y border-gray-100 bg-gray-50 dark:border-gray-800 dark:bg-gray-900">
          <TableRow>
            <TableCell isHeader className={HEADER_CELL_CLASS}>
              Request
            </TableCell>
            <TableCell isHeader className={HEADER_CELL_CLASS}>
              {isClubView ? "Status" : "Type"}
            </TableCell>
            <TableCell isHeader className={cn(HEADER_CELL_CLASS, WIDE_ONLY)}>
              Amount / When
            </TableCell>
            <TableCell isHeader className={cn(HEADER_CELL_CLASS, WIDE_ONLY)}>
              {isClubView ? "Updated" : "Waiting"}
            </TableCell>
          </TableRow>
        </TableHeader>

        <TableBody className="divide-y divide-gray-100 dark:divide-gray-800">
          {requests.map((request) => (
            <TableRow key={request.id}>
              <TableCell className="max-w-sm px-6 py-4 text-start">
                <Link
                  to={`/requests/${request.id}`}
                  className="text-sm font-medium break-words text-gray-800 hover:text-brand-500 dark:text-white/90 dark:hover:text-brand-400"
                >
                  {request.title}
                </Link>
                <p className="mt-0.5 truncate text-sm text-gray-500 dark:text-gray-400">
                  {isClubView
                    ? REQUEST_TYPE_LABELS[request.request_type]
                    : request.club_name}
                </p>
              </TableCell>
              <TableCell className="px-6 py-4 text-start text-sm text-gray-500 dark:text-gray-400">
                {isClubView ? (
                  <RequestStatusBadge status={request.status} />
                ) : (
                  REQUEST_TYPE_LABELS[request.request_type]
                )}
              </TableCell>
              <TableCell className={cn(CELL_CLASS, WIDE_ONLY)}>
                <AmountOrWhen request={request} />
              </TableCell>
              <TableCell
                className={cn(CELL_CLASS, WIDE_ONLY, "whitespace-nowrap")}
              >
                {isClubView
                  ? formatRelativeTime(request.updated_at)
                  : formatWaiting(request.updated_at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

/** The total for a funding request; the room and time for a booking. */
function AmountOrWhen({ request }: { request: RequestListItem }) {
  if (request.total_cents !== null)
    return <>{formatCents(request.total_cents)}</>;
  if (!request.room_name || !request.starts_at || !request.ends_at) return null;

  return (
    <>
      <span className="block">{request.room_name}</span>
      <span className="block">
        {formatTimeRange(request.starts_at, request.ends_at)}
      </span>
    </>
  );
}
