import AppLayout from "@/components/layout/app-layout";
import { RequireAdmin } from "@/components/shared/require-admin";
import { RequireAuth } from "@/components/shared/require-auth";
import ClubDetailPage from "@/pages/main/clubs/club-detail-page";
import ClubsPage from "@/pages/main/clubs/clubs-page";
import NewClubPage from "@/pages/main/clubs/new-club-page";
import ReviewQueuePage from "@/pages/main/clubs/review-queue-page";
import { Error404Page } from "@/pages/main/pages";
import { AuthLayout, SignInPage, SignUpPage } from "@/pages/others/auth";
import { Route, Routes } from "react-router";

export default function App() {
  return (
    <Routes>
      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route index element={<ClubsPage />} />
          <Route path="/clubs/new" element={<NewClubPage />} />
          <Route path="/clubs/:clubId" element={<ClubDetailPage />} />
          <Route element={<RequireAdmin />}>
            <Route path="/review" element={<ReviewQueuePage />} />
          </Route>
        </Route>
      </Route>

      <Route element={<AuthLayout />}>
        <Route path="/signin" element={<SignInPage />} />
        <Route path="/signup" element={<SignUpPage />} />
      </Route>

      <Route path="*" element={<Error404Page />} />
    </Routes>
  );
}
