import { CLUB_STATUS_BADGES, CLUB_STATUSES } from "@/lib/labels";
import type { ClubStatus } from "@/lib/types";

/** How many clubs are in each status, across all clubs. */
export function StatusSummary({
  counts,
}: {
  counts: Record<ClubStatus, number>;
}) {
  return (
    <section
      aria-label="Clubs by status"
      className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-6"
    >
      {CLUB_STATUSES.map((status) => (
        <div
          key={status}
          className="rounded-2xl border border-gray-200 bg-white px-5 py-4 dark:border-gray-800 dark:bg-white/3"
        >
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {CLUB_STATUS_BADGES[status].label}
          </p>
          <p className="mt-1 text-title-sm font-semibold text-gray-800 dark:text-white/90">
            {counts[status]}
          </p>
        </div>
      ))}
    </section>
  );
}
