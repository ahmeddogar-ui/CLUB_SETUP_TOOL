import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/contexts";
import { PlusIcon } from "@/icons";
import { apiFetch } from "@/lib/api";
import type { Club } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { ClubsTable } from "./clubs-table";

export default function ClubsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const clubs = useQuery({
    queryKey: ["clubs"],
    queryFn: () => apiFetch<Club[]>("/clubs"),
  });

  return (
    <div>
      <PageMeta
        title="Clubs | Club Setup"
        description="Clubs and their registration status"
      />
      <PageBreadcrumb pageTitle={isAdmin ? "All clubs" : "My clubs"} />

      <Card className="w-full gap-0 overflow-hidden rounded-2xl border border-gray-200 bg-white p-0 sm:p-0 dark:border-gray-800 dark:bg-white/3">
        <div className="flex items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <CardTitle className="text-lg font-semibold text-gray-800 dark:text-white/90">
            Clubs
          </CardTitle>
          {!isAdmin && (
            <Button
              size="sm"
              nativeButton={false}
              render={<Link to="/clubs/new" />}
            >
              <PlusIcon className="size-5" />
              New club
            </Button>
          )}
        </div>

        <ClubsTable
          clubs={clubs.data}
          isLoading={clubs.isLoading}
          error={clubs.error}
          emptyTitle="No clubs yet"
          emptyDescription={
            isAdmin
              ? "No club has been registered yet."
              : "Start by creating your club, then hand in its documents."
          }
        />
      </Card>
    </div>
  );
}
