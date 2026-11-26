import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/contexts";
import { Navigate, Outlet, useLocation } from "react-router";

const HOME_PATH = "/";

/** Keeps signed-out visitors off protected pages. Someone opening the bare
 * site sees the landing page; a deep link goes straight to sign-in. */
export function RequireAuth() {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner className="size-6 text-brand-500" />
      </div>
    );
  }

  if (!user) {
    const isHome = location.pathname === HOME_PATH;
    return <Navigate to={isHome ? "/welcome" : "/signin"} replace />;
  }

  return <Outlet />;
}
