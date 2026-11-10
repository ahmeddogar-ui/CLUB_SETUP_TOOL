import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown";
import { useAuth } from "@/contexts";
import { useTranslations } from "@/i18n";
import { ChevronDownIcon, LogOutIcon } from "@/icons";
import { cn, getInitials } from "@/utils";
import { useState } from "react";

export default function UserDropdown() {
  const t = useTranslations("userDropdown");
  const { user, signOut } = useAuth();
  const name = user?.name ?? "";
  const [isOpen, setIsOpen] = useState(false);

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger className="dropdown-toggle flex items-center text-gray-700 dark:text-gray-400">
        <Avatar size="lg" className="me-3">
          <AvatarFallback>{getInitials(name)}</AvatarFallback>
        </Avatar>

        <span className="me-1 block text-sm font-medium">{name}</span>

        <ChevronDownIcon
          className={cn(
            "size-5 text-gray-500 duration-200 dark:text-gray-400",
            isOpen ? "rotate-180" : "rotate-0",
          )}
        />
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" sideOffset={12} className="w-65 p-3">
        <div className="px-3 py-2">
          <span className="block text-sm font-medium text-gray-700 dark:text-gray-400">
            {name}
          </span>
          <span className="mt-0.5 block text-xs text-gray-500 dark:text-gray-400">
            {user?.email}
          </span>
        </div>

        <DropdownMenuSeparator />

        <DropdownMenuItem variant="destructive" onClick={signOut}>
          <LogOutIcon />
          {t("signOut")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
