import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { Card, CardTitle } from "@/components/ui/card";
import { apiFetch } from "@/lib/api";
import type { Club } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";
import { ClubsTable } from "./clubs-table";

const QUEUE_QUERY = "status=submitted&status=under_review&sort=oldest";

export default function ReviewQueuePage() {
  const queue = useQuery({
    queryKey: ["clubs", "review-queue"],
    queryFn: () => apiFetch<Club[]>(`/clubs?${QUEUE_QUERY}`),
  });

  return (
    <div>
      <PageMeta
        title="Review queue | Club Setup"
        description="Clubs waiting for review"
      />
      <PageBreadcrumb pageTitle="Review queue" />

      <Card className="w-full gap-0 overflow-hidden rounded-2xl border border-gray-200 bg-white p-0 sm:p-0 dark:border-gray-800 dark:bg-white/3">
        <div className="px-4 py-4 sm:px-6">
          <CardTitle className="text-lg font-semibold text-gray-800 dark:text-white/90">
            Waiting for review
          </CardTitle>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Longest waiting first.
          </p>
        </div>

        <ClubsTable
          clubs={queue.data}
          isLoading={queue.isLoading}
          error={queue.error}
          emptyTitle="Queue is empty"
          emptyDescription="No club is waiting for review."
        />
      </Card>
    </div>
  );
}
