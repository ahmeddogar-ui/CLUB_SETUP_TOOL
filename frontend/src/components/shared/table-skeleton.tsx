import { Skeleton } from "@/components/ui/skeleton";

interface TableSkeletonProps {
  /** Read out by screen readers, e.g. "Loading clubs". */
  label: string;
  rows?: number;
}

const DEFAULT_ROWS = 5;

/** Placeholder rows in the shape of a table, shown while a page loads. */
export function TableSkeleton({
  label,
  rows = DEFAULT_ROWS,
}: TableSkeletonProps) {
  return (
    <div
      role="status"
      aria-label={label}
      className="divide-y divide-gray-100 border-t border-gray-100 dark:divide-gray-800 dark:border-gray-800"
    >
      {Array.from({ length: rows }, (_, row) => (
        <div key={row} className="flex items-center gap-6 px-6 py-4">
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-1/3 bg-gray-200 dark:bg-gray-800" />
            <Skeleton className="h-3 w-2/3 bg-gray-100 dark:bg-gray-800/60" />
          </div>
          <Skeleton className="hidden h-5 w-20 rounded-full bg-gray-200 sm:block dark:bg-gray-800" />
          <Skeleton className="hidden h-4 w-24 bg-gray-100 md:block dark:bg-gray-800/60" />
        </div>
      ))}
    </div>
  );
}
