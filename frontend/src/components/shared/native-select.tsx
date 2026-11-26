import { cn } from "@/utils";
import type { ComponentProps } from "react";

/** A browser-native `<select>` styled like `Input`. Pass the `<option>`s as
 * children and an `aria-label` or an associated label. */
export function NativeSelect({
  className,
  ...props
}: ComponentProps<"select">) {
  return (
    <select
      className={cn(
        "h-9 rounded-[10px] border border-gray-300 bg-white px-3 text-sm text-gray-800 shadow-theme-xs outline-hidden transition-colors focus:border-brand-300 focus:ring-3 focus:ring-brand-500/20 disabled:cursor-not-allowed disabled:bg-gray-100/50 disabled:text-gray-400 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-500/40 dark:disabled:bg-gray-800/50 dark:disabled:text-gray-500",
        className,
      )}
      {...props}
    />
  );
}
