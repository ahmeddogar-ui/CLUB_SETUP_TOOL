import AppLayout from "@/components/layout/app-layout";
import { RequireAdmin } from "@/components/shared/require-admin";
import { RequireAuth } from "@/components/shared/require-auth";
import ActivityPage from "@/pages/main/activity/activity-page";
import UsersPage from "@/pages/main/users/users-page";
import ClubDetailPage from "@/pages/main/clubs/club-detail-page";
import ClubsPage from "@/pages/main/clubs/clubs-page";
import NewClubPage from "@/pages/main/clubs/new-club-page";
import ReviewQueuePage from "@/pages/main/clubs/review-queue-page";
import { useTheme } from "@/contexts";
import { Error404Page } from "@/pages/main/pages";
import ProfilePage from "@/pages/main/profile/profile-page";
import LandingPage from "@/pages/others/landing/landing-page";
import { AuthLayout, SignInPage, SignUpPage } from "@/pages/others/auth";
import { Route, Routes } from "react-router";
import { Toaster } from "sonner";

export default function App() {
  const { theme } = useTheme();

  return (
    <>
      <Toaster theme={theme} position="top-right" richColors closeButton />
      <Routes>
        <Route element={<RequireAuth />}>
          <Route element={<AppLayout />}>
            <Route index element={<ClubsPage />} />
            <Route path="/clubs/new" element={<NewClubPage />} />
            <Route path="/clubs/:clubId" element={<ClubDetailPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route element={<RequireAdmin />}>
              <Route path="/review" element={<ReviewQueuePage />} />
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
