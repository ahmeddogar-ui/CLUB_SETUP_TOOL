import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/contexts";
import { Navigate, Outlet } from "react-router";

export function RequireAuth() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner className="size-6 text-brand-500" />
      </div>
    );
  }

  if (!user) return <Navigate to="/signin" replace />;

  return <Outlet />;
}
