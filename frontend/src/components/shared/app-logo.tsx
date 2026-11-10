import { cn } from "@/utils";

const APP_NAME = "Club Setup";

interface AppLogoProps {
  showName?: boolean;
  className?: string;
  nameClassName?: string;
}

export function AppLogo({
  showName = true,
  className,
  nameClassName,
}: AppLogoProps) {
  return (
    <span className={cn("flex items-center gap-3", className)}>
      <img src="/images/logo/logo-icon.svg" alt="" className="size-8" />
      {showName && (
        <span
          className={cn(
            "text-xl font-semibold text-gray-800 dark:text-white/90",
            nameClassName,
          )}
        >
          {APP_NAME}
        </span>
      )}
    </span>
  );
}
