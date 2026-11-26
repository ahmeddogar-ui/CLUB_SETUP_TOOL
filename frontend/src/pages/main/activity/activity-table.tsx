import { EmptyList, ListError } from "@/components/shared/list-states";
import { TableSkeleton } from "@/components/shared/table-skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EVENT_LABELS, formatDateTime, REQUIREMENT_LABELS } from "@/lib/labels";
import type { ActivityEntry } from "@/lib/types";
import { cn } from "@/utils";

const HEADER_CELL_CLASS =
  "px-6 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400";
const CELL_CLASS =
  "px-6 py-4 text-start text-sm text-gray-500 dark:text-gray-400";
const WIDE_ONLY = "hidden md:table-cell";
const FILTER_BUTTON_CLASS =
  "text-start text-gray-800 hover:text-brand-500 dark:text-white/90 dark:hover:text-brand-400";

interface ActivityTableProps {
  entries: ActivityEntry[] | undefined;
  /** True on the first load and while another page or filter loads. */
  isLoading: boolean;
  error: Error | null;
  onFilterActor: (actorId: number) => void;
  onFilterClub: (clubId: number) => void;
  onClearFilters: () => void;
}

export function ActivityTable({
  entries,
  isLoading,
  error,
  onFilterActor,
  onFilterClub,
  onClearFilters,
}: ActivityTableProps) {
  if (isLoading) return <TableSkeleton label="Loading activity" />;
  if (error) {
    return (
      <ListError title="Could not load activity" message={error.message} />
    );
  }
  if (!entries || entries.length === 0) {
    return (
      <EmptyList
        title="No activity matches"
        description="Try another action or date range, or clear the filters."
        actionLabel="Clear filters"
        onAction={onClearFilters}
      />
    );
  }

  return (
    <div className="max-w-full overflow-x-auto">
      <Table>
        <TableHeader className="border-y border-gray-100 bg-gray-50 dark:border-gray-800 dark:bg-gray-900">
          <TableRow>
            <TableCell isHeader className={HEADER_CELL_CLASS}>
              When
            </TableCell>
            <TableCell isHeader className={HEADER_CELL_CLASS}>
              Who
            </TableCell>
            <TableCell isHeader className={HEADER_CELL_CLASS}>
              Action
            </TableCell>
            <TableCell isHeader className={HEADER_CELL_CLASS}>
              Club
            </TableCell>
            <TableCell isHeader className={cn(HEADER_CELL_CLASS, WIDE_ONLY)}>
              Note
            </TableCell>
          </TableRow>
        </TableHeader>

        <TableBody className="divide-y divide-gray-100 dark:divide-gray-800">
          {entries.map((entry) => (
            <TableRow key={entry.id}>
              <TableCell className={cn(CELL_CLASS, "whitespace-nowrap")}>
                {formatDateTime(entry.created_at)}
              </TableCell>
              <TableCell className={CELL_CLASS}>
                <button
                  type="button"
                  aria-label={`Show activity by ${entry.actor_name}`}
                  onClick={() => onFilterActor(entry.actor_id)}
                  className={FILTER_BUTTON_CLASS}
                >
                  {entry.actor_name}
                </button>
              </TableCell>
              <TableCell className={CELL_CLASS}>{actionLabel(entry)}</TableCell>
              <TableCell className={CELL_CLASS}>
                <SubjectCell entry={entry} onFilterClub={onFilterClub} />
              </TableCell>
              <TableCell className={cn(CELL_CLASS, WIDE_ONLY, "max-w-xs")}>
                <p className="truncate">{entry.note}</p>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

/** "Requirement approved · Budget" for requirement events. */
function actionLabel(entry: ActivityEntry): string {
  const label = EVENT_LABELS[entry.event_type];
  if (!entry.requirement_type) return label;
  return `${label} · ${REQUIREMENT_LABELS[entry.requirement_type]}`;
}

/** The club, as a filter button; a role change has no club, so it names the
 * user whose role changed. */
function SubjectCell({
  entry,
  onFilterClub,
}: {
  entry: ActivityEntry;
  onFilterClub: (clubId: number) => void;
}) {
  if (entry.club_id !== null && entry.club_name !== null) {
    const clubId = entry.club_id;
    return (
      <button
        type="button"
        onClick={() => onFilterClub(clubId)}
        className={FILTER_BUTTON_CLASS}
      >
        {entry.club_name}
      </button>
    );
  }
  return <span>{entry.subject_user_name}</span>;
}
