import { useAuth } from "@/contexts";
import { Navigate, Outlet } from "react-router";

export function RequireAdmin() {
  const { user } = useAuth();

  if (user?.role !== "admin") return <Navigate to="/" replace />;

  return <Outlet />;
}
