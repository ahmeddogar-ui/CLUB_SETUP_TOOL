import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { Pager } from "@/components/shared/pager";
import { Card } from "@/components/ui/card";
import { apiFetch } from "@/lib/api";
import type { Page, UserListItem, UserRole } from "@/lib/types";
import { readPage } from "@/pages/main/clubs/club-page-query";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router";
import { UserFilters } from "./user-filters";
import { UsersTable } from "./users-table";

const USERS_PAGE_SIZE = 20;

/** Every user, for admins to find and change roles. The search, role and page
 * live in the URL, so they survive a reload and the back button. */
export default function UsersPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const roleParam = searchParams.get("role");
  const role: UserRole | null =
    roleParam === "admin" || roleParam === "club_lead" ? roleParam : null;
  const search = searchParams.get("q") ?? "";
  const page = readPage(searchParams);

  const filters = { search, role, page };
  const users = useQuery({
    queryKey: ["users", "list", filters],
    queryFn: () => {
      const params = new URLSearchParams({
        limit: String(USERS_PAGE_SIZE),
        offset: String((page - 1) * USERS_PAGE_SIZE),
      });
      if (search) params.set("q", search);
      if (role) params.set("role", role);
      return apiFetch<Page<UserListItem>>(`/users?${params}`);
    },
    placeholderData: keepPreviousData,
  });

  // A new filter starts again from page 1.
  const showFilters = (next: { role: UserRole | null; search: string }) => {
    const params = new URLSearchParams();
    if (next.role) params.set("role", next.role);
    if (next.search) params.set("q", next.search);
    setSearchParams(params);
  };

  const showPage = (nextPage: number) => {
    const params = new URLSearchParams(searchParams);
    params.set("page", String(nextPage));
    setSearchParams(params);
  };

  return (
    <div>
      <PageMeta title="Users" description="Find users and change their role" />
      <PageBreadcrumb pageTitle="Users" />

      <Card className="w-full gap-0 overflow-hidden rounded-2xl border border-gray-200 bg-white p-0 sm:p-0 dark:border-gray-800 dark:bg-white/3">
        <UserFilters role={role} search={search} onChange={showFilters} />
        <UsersTable
          users={users.data?.items}
          isLoading={users.isLoading || users.isPlaceholderData}
          error={users.error}
          onClearFilters={() => showFilters({ role: null, search: "" })}
        />
        <Pager
          page={page}
          pageSize={USERS_PAGE_SIZE}
          total={users.data?.total ?? 0}
          onPageChange={showPage}
        />
      </Card>
    </div>
  );
}
