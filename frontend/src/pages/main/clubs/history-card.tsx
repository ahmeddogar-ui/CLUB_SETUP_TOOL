import { Card, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EVENT_LABELS, formatDateTime, REQUIREMENT_LABELS } from "@/lib/labels";
import type { ClubEvent, Requirement } from "@/lib/types";

const HEADER_CELL_CLASS =
  "px-6 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400";

interface HistoryCardProps {
  events: ClubEvent[];
  requirements: Requirement[];
}

export function HistoryCard({ events, requirements }: HistoryCardProps) {
  const requirementLabel = (requirementId: number | null) => {
    const requirement = requirements.find((row) => row.id === requirementId);
    return requirement
      ? REQUIREMENT_LABELS[requirement.requirement_type]
      : null;
  };

  return (
    <Card className="w-full gap-0 overflow-hidden rounded-2xl border border-gray-200 bg-white p-0 sm:p-0 dark:border-gray-800 dark:bg-white/3">
      <div className="px-4 py-4 sm:px-6">
        <CardTitle className="text-lg font-semibold text-gray-800 dark:text-white/90">
          History
        </CardTitle>
      </div>

      <div className="max-w-full overflow-x-auto">
        <Table>
          <TableHeader className="border-y border-gray-100 bg-gray-50 dark:border-gray-800 dark:bg-gray-900">
            <TableRow>
              <TableCell isHeader className={HEADER_CELL_CLASS}>
                When
              </TableCell>
              <TableCell isHeader className={HEADER_CELL_CLASS}>
                Event
              </TableCell>
              <TableCell isHeader className={HEADER_CELL_CLASS}>
                By
              </TableCell>
              <TableCell isHeader className={HEADER_CELL_CLASS}>
                Note
              </TableCell>
            </TableRow>
          </TableHeader>

          <TableBody className="divide-y divide-gray-100 dark:divide-gray-800">
            {events.map((event) => {
              const subject = requirementLabel(event.requirement_id);

              return (
                <TableRow key={event.id}>
                  <TableCell className="px-6 py-4 text-start text-sm whitespace-nowrap text-gray-500 dark:text-gray-400">
                    {formatDateTime(event.created_at)}
                  </TableCell>
                  <TableCell className="px-6 py-4 text-start text-sm text-gray-800 dark:text-white/90">
                    {EVENT_LABELS[event.event_type] ?? event.event_type}
                    {subject && (
                      <span className="text-gray-500 dark:text-gray-400">
                        {" "}
                        · {subject}
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="px-6 py-4 text-start text-sm text-gray-700 dark:text-gray-400">
                    {event.actor_name}
                  </TableCell>
                  <TableCell className="px-6 py-4 text-start text-sm text-gray-700 dark:text-gray-400">
                    {event.note}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </Card>
  );
}
