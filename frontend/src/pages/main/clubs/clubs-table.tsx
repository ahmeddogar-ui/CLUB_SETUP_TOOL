import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { BoxIcon, OctagonAlertIcon } from "@/icons";
import { formatRelativeTime, formatWaiting } from "@/lib/labels";
import type { ClubListItem } from "@/lib/types";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { ClubStatusBadge } from "./status-badge";

const HEADER_CELL_CLASS =
  "px-6 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400";
const CELL_CLASS =
  "px-6 py-4 text-start text-sm whitespace-nowrap text-gray-500 dark:text-gray-400";

export interface EmptyState {
  title: string;
  description: string;
  action: ReactNode;
}

interface ClubsTableProps {
  clubs: ClubListItem[] | undefined;
  isLoading: boolean;
  error: Error | null;
  /** Admins see clubs from every lead, so they need to know whose each is. */
  showOwner: boolean;
  /** The review queue shows how long each club has waited instead. */
  timeColumn: "last-updated" | "waiting";
  emptyState: EmptyState;
}

export function ClubsTable({
  clubs,
  isLoading,
  error,
  showOwner,
  timeColumn,
  emptyState,
}: ClubsTableProps) {
  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner className="size-6 text-brand-500" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive" className="m-6 w-auto p-4">
        <OctagonAlertIcon className="size-5" />
        <AlertTitle>Could not load clubs</AlertTitle>
        <AlertDescription>{error.message}</AlertDescription>
      </Alert>
    );
  }

  if (!clubs || clubs.length === 0) {
    return <EmptyClubs {...emptyState} />;
  }

  return (
    <div className="max-w-full overflow-x-auto">
      <Table>
        <TableHeader className="border-y border-gray-100 bg-gray-50 dark:border-gray-800 dark:bg-gray-900">
          <TableRow>
            <TableCell isHeader className={HEADER_CELL_CLASS}>
              Club
            </TableCell>
            {showOwner && (
              <TableCell isHeader className={HEADER_CELL_CLASS}>
                Owner
              </TableCell>
            )}
            <TableCell isHeader className={HEADER_CELL_CLASS}>
              Status
            </TableCell>
            <TableCell isHeader className={HEADER_CELL_CLASS}>
              Documents
            </TableCell>
            <TableCell isHeader className={HEADER_CELL_CLASS}>
              {timeColumn === "waiting" ? "Waiting" : "Last updated"}
            </TableCell>
          </TableRow>
        </TableHeader>

        <TableBody className="divide-y divide-gray-100 dark:divide-gray-800">
          {clubs.map((club) => (
            <TableRow key={club.id}>
              <TableCell className="max-w-sm px-6 py-4 text-start">
                <Link
                  to={`/clubs/${club.id}`}
                  className="text-sm font-medium text-gray-800 hover:text-brand-500 dark:text-white/90 dark:hover:text-brand-400"
                >
                  {club.name}
                </Link>
                <p className="mt-0.5 truncate text-sm text-gray-500 dark:text-gray-400">
                  {club.description}
                </p>
              </TableCell>
              {showOwner && (
                <TableCell className={CELL_CLASS}>{club.owner_name}</TableCell>
              )}
              <TableCell className="px-6 py-4 text-start">
                <ClubStatusBadge status={club.status} />
              </TableCell>
              <TableCell className={CELL_CLASS}>
                {club.documents_provided}/{club.documents_total} documents
              </TableCell>
              <TableCell className={CELL_CLASS}>
                {timeColumn === "waiting"
                  ? formatWaiting(club.updated_at)
                  : formatRelativeTime(club.updated_at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function EmptyClubs({ title, description, action }: EmptyState) {
  return (
    <div className="flex flex-col items-center justify-center border-t border-gray-100 px-6 py-12 text-center dark:border-gray-800">
      <div className="mb-3 flex size-12 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800">
        <BoxIcon className="size-6 text-gray-800 dark:text-white/90" />
      </div>
      <h4 className="text-base font-semibold text-gray-800 dark:text-white/90">
        {title}
      </h4>
      <p className="mt-1 mb-5 text-sm text-gray-500 dark:text-gray-400">
        {description}
      </p>
      {action}
    </div>
  );
}
