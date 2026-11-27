import { Card, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatCents, formatTimeRange } from "@/lib/request-labels";
import type { RequestDetail } from "@/lib/request-types";

const HEADER_CELL_CLASS =
  "px-6 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400";
const CELL_CLASS = "px-6 py-4 text-sm text-gray-700 dark:text-gray-400";

export function RequestDetailsCard({
  details,
}: Pick<RequestDetail, "details">) {
  return (
    <Card className="w-full gap-0 overflow-hidden rounded-2xl border border-gray-200 bg-white p-0 sm:p-0 dark:border-gray-800 dark:bg-white/3">
      <div className="px-4 py-4 sm:px-6">
        <CardTitle className="text-lg font-semibold text-gray-800 dark:text-white/90">
          Details
        </CardTitle>
      </div>

      {details.request_type === "funding" ? (
        <div className="max-w-full overflow-x-auto">
          <Table>
            <TableHeader className="border-y border-gray-100 bg-gray-50 dark:border-gray-800 dark:bg-gray-900">
              <TableRow>
                <TableCell isHeader className={HEADER_CELL_CLASS}>
                  Description
                </TableCell>
                <TableCell
                  isHeader
                  className={`${HEADER_CELL_CLASS} text-right`}
                >
                  Amount
                </TableCell>
              </TableRow>
            </TableHeader>
            <TableBody className="divide-y divide-gray-100 dark:divide-gray-800">
              {details.line_items.map((item, index) => (
                <TableRow key={index}>
                  <TableCell className={`${CELL_CLASS} text-start`}>
                    {item.description}
                  </TableCell>
                  <TableCell className={`${CELL_CLASS} text-right`}>
                    {formatCents(item.amount_cents)}
                  </TableCell>
                </TableRow>
              ))}
              <TableRow>
                <TableCell
                  className={`${CELL_CLASS} text-start font-semibold text-gray-800 dark:text-white/90`}
                >
                  Total
                </TableCell>
                <TableCell
                  className={`${CELL_CLASS} text-right font-semibold text-gray-800 dark:text-white/90`}
                >
                  {formatCents(details.total_cents)}
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      ) : (
        <dl className="grid gap-4 border-t border-gray-100 px-4 py-4 text-sm sm:grid-cols-2 sm:px-6 dark:border-gray-800">
          <div>
            <dt className="text-gray-500 dark:text-gray-400">Room</dt>
            <dd className="mt-1 text-gray-800 dark:text-white/90">
              {details.room_name}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500 dark:text-gray-400">When</dt>
            <dd className="mt-1 text-gray-800 dark:text-white/90">
              {formatTimeRange(details.starts_at, details.ends_at)}
            </dd>
          </div>
        </dl>
      )}
    </Card>
  );
}
