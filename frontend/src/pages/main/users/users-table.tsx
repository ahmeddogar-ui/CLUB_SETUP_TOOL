import { EmptyList, ListError } from "@/components/shared/list-states";
import { NativeSelect } from "@/components/shared/native-select";
import { TableSkeleton } from "@/components/shared/table-skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuth } from "@/contexts";
import { apiFetch } from "@/lib/api";
import { formatDateTime, USER_ROLE_LABELS } from "@/lib/labels";
import type { User, UserListItem, UserRole } from "@/lib/types";
import { cn } from "@/utils";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

const HEADER_CELL_CLASS =
  "px-6 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400";
const CELL_CLASS =
  "px-6 py-4 text-start text-sm whitespace-nowrap text-gray-500 dark:text-gray-400";
const WIDE_ONLY = "hidden md:table-cell";

const ROLES = Object.keys(USER_ROLE_LABELS) as UserRole[];

interface UsersTableProps {
  users: UserListItem[] | undefined;
  /** True on the first load and while another page or filter loads. */
  isLoading: boolean;
  error: Error | null;
  onClearFilters: () => void;
}

export function UsersTable({
  users,
  isLoading,
  error,
  onClearFilters,
}: UsersTableProps) {
  const { user: signedInUser } = useAuth();

  if (isLoading) return <TableSkeleton label="Loading users" />;
  if (error) {
    return <ListError title="Could not load users" message={error.message} />;
  }
  if (!users || users.length === 0) {
    return (
      <EmptyList
        title="No users match"
        description="Try another role, or search for a different name or email."
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
              Name
            </TableCell>
            <TableCell isHeader className={HEADER_CELL_CLASS}>
              Role
            </TableCell>
            <TableCell isHeader className={cn(HEADER_CELL_CLASS, WIDE_ONLY)}>
              Joined
            </TableCell>
          </TableRow>
        </TableHeader>

        <TableBody className="divide-y divide-gray-100 dark:divide-gray-800">
          {users.map((user) => (
            <TableRow key={user.id}>
              <TableCell className="px-6 py-4 text-start">
                <p className="text-sm font-medium break-words text-gray-800 dark:text-white/90">
                  {user.name}
                </p>
                <p className="mt-0.5 text-sm break-all text-gray-500 dark:text-gray-400">
                  {user.email}
                </p>
              </TableCell>
              <TableCell className={CELL_CLASS}>
                {user.id === signedInUser?.id ? (
                  `${USER_ROLE_LABELS[user.role]} (you)`
                ) : (
                  <RoleSelect user={user} />
                )}
              </TableCell>
              <TableCell className={cn(CELL_CLASS, WIDE_ONLY)}>
                {formatDateTime(user.created_at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function RoleSelect({ user }: { user: UserListItem }) {
  const queryClient = useQueryClient();
  const changeRole = useMutation({
    mutationFn: (role: UserRole) =>
      apiFetch<User>(`/users/${user.id}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      }),
    meta: {
      successMessage: (role: UserRole) =>
        `${user.name} is now ${USER_ROLE_LABELS[role]}`,
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
    onError: (error) => toast.error(error.message),
  });

  return (
    <NativeSelect
      aria-label={`Role for ${user.name}`}
      value={user.role}
      disabled={changeRole.isPending}
      onChange={(event) => changeRole.mutate(event.target.value as UserRole)}
    >
      {ROLES.map((role) => (
        <option key={role} value={role}>
          {USER_ROLE_LABELS[role]}
        </option>
      ))}
    </NativeSelect>
  );
}
