import AppLayout from "@/components/layout/app-layout";
import { RequireAuth } from "@/components/shared/require-auth";
import ActivityPage from "@/pages/main/activity/activity-page";
import UsersPage from "@/pages/main/users/users-page";
import { RequireRole } from "@/components/shared/require-role";
import ClubDetailPage from "@/pages/main/clubs/club-detail-page";
import ClubsPage from "@/pages/main/clubs/clubs-page";
import NewClubPage from "@/pages/main/clubs/new-club-page";
import ReviewQueuePage from "@/pages/main/clubs/review-queue-page";
import { useAuth, useTheme } from "@/contexts";
import EditRequestPage from "@/pages/main/requests/edit-request-page";
import NewRequestPage from "@/pages/main/requests/new-request-page";
import RequestDetailPage from "@/pages/main/requests/request-detail-page";
import { Error404Page } from "@/pages/main/pages";
import ProfilePage from "@/pages/main/profile/profile-page";
import LandingPage from "@/pages/others/landing/landing-page";
import { AuthLayout, SignInPage, SignUpPage } from "@/pages/others/auth";
import { Navigate, Route, Routes } from "react-router";
import { Toaster } from "sonner";

/** Finance approvers have no clubs, so their home is the review queue. */
function HomePage() {
  const { user } = useAuth();

  if (user?.role === "finance_approver") {
    return <Navigate to="/review" replace />;
  }
  return <ClubsPage />;
}

export default function App() {
  const { theme } = useTheme();

  return (
    <>
      <Toaster theme={theme} position="top-right" richColors closeButton />
      <Routes>
        <Route element={<RequireAuth />}>
          <Route element={<AppLayout />}>
            <Route index element={<HomePage />} />
            <Route path="/clubs/new" element={<NewClubPage />} />
            <Route path="/clubs/:clubId" element={<ClubDetailPage />} />
            <Route
              path="/clubs/:clubId/requests/new"
              element={<NewRequestPage />}
            />
            <Route
              path="/requests/:requestId"
              element={<RequestDetailPage />}
            />
            <Route
              path="/requests/:requestId/edit"
              element={<EditRequestPage />}
            />
            <Route path="/profile" element={<ProfilePage />} />
            <Route
              element={<RequireRole roles={["admin", "finance_approver"]} />}
            >
              <Route path="/review" element={<ReviewQueuePage />} />
            </Route>
            <Route element={<RequireRole roles={["admin"]} />}>
              <Route path="/users" element={<UsersPage />} />
              <Route path="/activity" element={<ActivityPage />} />
            </Route>
          </Route>
        </Route>

        <Route path="/welcome" element={<LandingPage />} />

        <Route element={<AuthLayout />}>
          <Route path="/signin" element={<SignInPage />} />
          <Route path="/signup" element={<SignUpPage />} />
        </Route>

        <Route path="*" element={<Error404Page />} />
      </Routes>
    </>
  );
}
