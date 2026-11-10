import { AppLogo } from "@/components/shared/app-logo";
import { SidebarHeader } from "@/components/ui/sidebar";
import { Link } from "react-router";

interface AppSidebarHeaderProps {
  showContent: boolean;
}

export default function AppSidebarHeader({
  showContent,
}: AppSidebarHeaderProps) {
  return (
    <SidebarHeader className="px-5 py-8">
      <Link to="/">
        <AppLogo showName={showContent} />
      </Link>
    </SidebarHeader>
  );
}
