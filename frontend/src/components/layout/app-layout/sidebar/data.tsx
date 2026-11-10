import { LayoutGridIcon, TaskIcon } from "@/icons";
import type { NavItem } from "./types";

export const navItems: NavItem[] = [
  {
    icon: <LayoutGridIcon className="size-6" />,
    key: "clubs",
    path: "/",
  },
  {
    icon: <TaskIcon className="size-6" />,
    key: "reviewQueue",
    path: "/review",
    isAdminOnly: true,
  },
];
