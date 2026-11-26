import { AppLogo } from "@/components/shared/app-logo";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import { useAuth } from "@/contexts";
import {
  ClockIcon,
  HorizontalDotsIcon,
  LayoutGridIcon,
  TaskIcon,
  UserIcon,
} from "@/icons";
import { cn } from "@/utils";
import { Link, useLocation } from "react-router";

const NAV_ITEMS = [
  {
    label: "Clubs",
    path: "/",
    icon: <LayoutGridIcon className="size-6" />,
    isAdminOnly: false,
  },
  {
    label: "Review queue",
    path: "/review",
    icon: <TaskIcon className="size-6" />,
    isAdminOnly: true,
  },
  {
    label: "Users",
    path: "/users",
    icon: <UserIcon className="size-6" />,
    isAdminOnly: true,
  },
  {
    label: "Activity",
    path: "/activity",
    icon: <ClockIcon className="size-6" />,
    isAdminOnly: true,
  },
];

/** Club pages (/clubs/new, /clubs/3) belong to the Clubs section. */
function isCurrentSection(itemPath: string, pathname: string): boolean {
  if (itemPath === "/")
    return pathname === "/" || pathname.startsWith("/clubs/");
  return pathname.startsWith(itemPath);
}

export default function AppSidebar() {
  const { open, isMobile, isHovered } = useSidebar();
  const { pathname } = useLocation();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  // A collapsed sidebar shows icons only, until hovered.
  const showLabels = open || isHovered || isMobile;
  const visibleItems = NAV_ITEMS.filter((item) => !item.isAdminOnly || isAdmin);

  return (
    <Sidebar side="left" collapsible="icon">
      <SidebarHeader className="px-5 py-8">
        <Link to="/">
          <AppLogo showName={showLabels} />
        </Link>
      </SidebarHeader>

      <SidebarContent className="overflow-y-auto px-5 duration-300 ease-linear">
        <nav className="mb-6">
          <SidebarGroup className="p-0">
            <SidebarGroupLabel
              className={cn(
                "mb-4 flex h-auto p-0 text-xs leading-5 text-gray-400 uppercase",
                showLabels ? "justify-start" : "xl:justify-center",
              )}
            >
              {showLabels ? "Menu" : <HorizontalDotsIcon />}
            </SidebarGroupLabel>
            <SidebarMenu className="gap-1">
              {visibleItems.map((item) => {
                const isActive = isCurrentSection(item.path, pathname);
                return (
                  <SidebarMenuItem key={item.path}>
                    <Link
                      to={item.path}
                      aria-current={isActive ? "page" : undefined}
                      className={cn(
                        "group menu-item",
                        isActive ? "menu-item-active" : "menu-item-inactive",
                      )}
                    >
                      <span
                        className={
                          isActive
                            ? "menu-item-icon-active"
                            : "menu-item-icon-inactive"
                        }
                      >
                        {item.icon}
                      </span>
                      {showLabels && <span>{item.label}</span>}
                    </Link>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroup>
        </nav>
      </SidebarContent>
    </Sidebar>
  );
}
