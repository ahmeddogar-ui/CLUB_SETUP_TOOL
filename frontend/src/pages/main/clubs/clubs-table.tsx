import { TableSkeleton } from "@/components/shared/table-skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { BoxIcon, ChevronDownIcon, OctagonAlertIcon } from "@/icons";
import { formatRelativeTime, formatWaiting } from "@/lib/labels";
import type { ClubListItem, ClubSortField } from "@/lib/types";
import { cn } from "@/utils";
import type { ReactNode } from "react";
import { Link } from "react-router";
import type { ClubSort } from "./club-page-query";
import { ClubStatusBadge } from "./status-badge";

const HEADER_CELL_CLASS =
  "px-6 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400";
const CELL_CLASS =
  "px-6 py-4 text-start text-sm whitespace-nowrap text-gray-500 dark:text-gray-400";
// Secondary columns give way on small screens; the club cell repeats the owner.
const WIDE_ONLY = "hidden md:table-cell";

export interface EmptyState {
  title: string;
  description: string;
  action: ReactNode;
}

/** Shown when the page in the URL is past the end of the list, e.g. after
 * the last club on it was reviewed, or from an old link. */
export function pastLastPage(goToFirstPage: () => void): EmptyState {
  return {
    title: "No clubs on this page",
    description: "The list is shorter than this page now.",
    action: (
      <Button size="sm" variant="outline" onClick={goToFirstPage}>
        Go to the first page
      </Button>
    ),
  };
}

interface Sorting {
  sort: ClubSort;
  onSortChange: (sort: ClubSort) => void;
}

interface ClubsTableProps {
  clubs: ClubListItem[] | undefined;
  /** True on the first load and while another page or filter loads. */
  isLoading: boolean;
  error: Error | null;
  /** Admins see clubs from every lead, so they need to know whose each is. */
  showOwner: boolean;
  /** The review queue shows how long each club has waited instead. */
  timeColumn: "last-updated" | "waiting";
  emptyState: EmptyState;
  /** Omit for a fixed order (the review queue). */
  sorting?: Sorting;
}

export function ClubsTable({
  clubs,
  isLoading,
  error,
  showOwner,
  timeColumn,
  emptyState,
  sorting,
}: ClubsTableProps) {
  if (isLoading) return <TableSkeleton label="Loading clubs" />;

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

  const header = (label: string, field: ClubSortField, className = "") => (
    <HeaderCell
      label={label}
      field={field}
      sorting={sorting}
      className={className}
    />
  );

  return (
    <div className="max-w-full overflow-x-auto">
      <Table className="table-fixed md:table-auto">
        <TableHeader className="border-y border-gray-100 bg-gray-50 dark:border-gray-800 dark:bg-gray-900">
          <TableRow>
            {header("Club", "name", "w-1/2 md:w-auto")}
            {showOwner && header("Owner", "owner", WIDE_ONLY)}
            {header("Status", "status")}
            <TableCell isHeader className={cn(HEADER_CELL_CLASS, WIDE_ONLY)}>
              Documents
            </TableCell>
            {timeColumn === "waiting" ? (
              <TableCell isHeader className={cn(HEADER_CELL_CLASS, WIDE_ONLY)}>
                Waiting
              </TableCell>
            ) : (
              header("Last updated", "updated", WIDE_ONLY)
            )}
          </TableRow>
        </TableHeader>

        <TableBody className="divide-y divide-gray-100 dark:divide-gray-800">
          {clubs.map((club) => (
            <TableRow key={club.id}>
              <TableCell className="max-w-sm px-6 py-4 text-start">
                <Link
                  to={`/clubs/${club.id}`}
                  className="text-sm font-medium break-words text-gray-800 hover:text-brand-500 dark:text-white/90 dark:hover:text-brand-400"
                >
                  {club.name}
                </Link>
                <p className="mt-0.5 truncate text-sm text-gray-500 dark:text-gray-400">
                  {club.description}
                </p>
                {showOwner && (
                  <p className="mt-0.5 truncate text-xs text-gray-400 md:hidden">
                    {club.owner_name}
                  </p>
                )}
              </TableCell>
              {showOwner && (
                <TableCell className={cn(CELL_CLASS, WIDE_ONLY)}>
                  {club.owner_name}
                </TableCell>
              )}
              <TableCell className="px-6 py-4 text-start">
                <ClubStatusBadge status={club.status} />
              </TableCell>
              <TableCell className={cn(CELL_CLASS, WIDE_ONLY)}>
                {club.documents_provided}/{club.documents_total} documents
              </TableCell>
              <TableCell className={cn(CELL_CLASS, WIDE_ONLY)}>
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

interface HeaderCellProps {
  label: string;
  field: ClubSortField;
  sorting: Sorting | undefined;
  className: string;
}

/** A column header; with sorting, a button that sorts by it (ascending
 * first, then flipping). */
function HeaderCell({ label, field, sorting, className }: HeaderCellProps) {
  if (!sorting) {
    return (
      <TableCell isHeader className={cn(HEADER_CELL_CLASS, className)}>
        {label}
      </TableCell>
    );
  }

  const { sort, onSortChange } = sorting;
  const isActive = sort.field === field;
  const nextOrder = isActive && sort.order === "asc" ? "desc" : "asc";

  return (
    <TableCell
      isHeader
      className={cn(HEADER_CELL_CLASS, className)}
      aria-sort={
        isActive ? (sort.order === "asc" ? "ascending" : "descending") : "none"
      }
    >
      <button
        type="button"
        onClick={() => onSortChange({ field, order: nextOrder })}
        className={cn(
          "inline-flex items-center gap-1 hover:text-gray-800 dark:hover:text-white/90",
          isActive && "text-gray-800 dark:text-white/90",
        )}
      >
        {label}
        <ChevronDownIcon
          aria-hidden
          className={cn(
            "size-4 transition-transform",
            !isActive && "opacity-0",
            isActive && sort.order === "asc" && "rotate-180",
          )}
        />
      </button>
    </TableCell>
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
