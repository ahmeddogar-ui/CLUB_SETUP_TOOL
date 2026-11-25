import AppHeader from "@/components/layout/app-layout/header";
import AppSidebar from "@/components/layout/app-layout/sidebar";
import { ScrollToTop } from "@/components/shared/scroll-to-top";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { Outlet } from "react-router";

export default function AppLayout() {
  return (
    <SidebarProvider>
      <AppSidebar />

      <SidebarInset>
        <AppHeader />

        <div className="mx-auto w-full max-w-(--breakpoint-2xl) p-4 md:p-6">
          <Outlet />
        </div>
      </SidebarInset>
      <ScrollToTop />
    </SidebarProvider>
  );
}
