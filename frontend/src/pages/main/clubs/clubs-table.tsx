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
import type { Club } from "@/lib/types";
import { Link } from "react-router";
import { ClubStatusBadge } from "./status-badge";

const HEADER_CELL_CLASS =
  "px-6 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400";

interface ClubsTableProps {
  clubs: Club[] | undefined;
  isLoading: boolean;
  error: Error | null;
  emptyTitle: string;
  emptyDescription: string;
}

export function ClubsTable({
  clubs,
  isLoading,
  error,
  emptyTitle,
  emptyDescription,
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

  return (
    <div className="max-w-full overflow-x-auto">
      <Table>
        <TableHeader className="border-y border-gray-100 bg-gray-50 dark:border-gray-800 dark:bg-gray-900">
          <TableRow>
            <TableCell isHeader className={HEADER_CELL_CLASS}>
              Club
            </TableCell>
            <TableCell isHeader className={HEADER_CELL_CLASS}>
              Description
            </TableCell>
            <TableCell isHeader className={HEADER_CELL_CLASS}>
              Status
            </TableCell>
          </TableRow>
        </TableHeader>

        <TableBody className="divide-y divide-gray-100 dark:divide-gray-800">
          {clubs && clubs.length > 0 ? (
            clubs.map((club) => (
              <TableRow key={club.id}>
                <TableCell className="px-6 py-4 text-start">
                  <Link
                    to={`/clubs/${club.id}`}
                    className="text-sm font-medium text-gray-800 hover:text-brand-500 dark:text-white/90 dark:hover:text-brand-400"
                  >
                    {club.name}
                  </Link>
                </TableCell>
                <TableCell className="max-w-md truncate px-6 py-4 text-start text-sm text-gray-500 dark:text-gray-400">
                  {club.description}
                </TableCell>
                <TableCell className="px-6 py-4 text-start">
                  <ClubStatusBadge status={club.status} />
                </TableCell>
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell
                colSpan={3}
                className="px-6 py-12 text-center text-sm text-gray-500 dark:text-gray-400"
              >
                <div className="flex flex-col items-center justify-center">
                  <div className="mb-3 flex size-12 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800">
                    <BoxIcon className="size-6 text-gray-800 dark:text-white/90" />
                  </div>
                  <h4 className="text-base font-semibold text-gray-800 dark:text-white/90">
                    {emptyTitle}
                  </h4>
                  <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    {emptyDescription}
                  </p>
                </div>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
