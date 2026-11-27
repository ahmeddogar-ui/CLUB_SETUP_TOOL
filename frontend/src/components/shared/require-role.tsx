import { useAuth } from "@/contexts";
import type { UserRole } from "@/lib/types";
import { Navigate, Outlet } from "react-router";

/** Sends anyone whose role isn't in `roles` back to the home page. */
export function RequireRole({ roles }: { roles: readonly UserRole[] }) {
  const { user } = useAuth();

  if (!user || !roles.includes(user.role)) return <Navigate to="/" replace />;

  return <Outlet />;
}
