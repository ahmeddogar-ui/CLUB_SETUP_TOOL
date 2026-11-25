import { type ClassValue, clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

// tailwind-merge only knows Tailwind's built-in scale; these are the custom
// theme tokens from index.css that must override their built-in counterparts.
const customTwMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": ["text-title-sm", "text-title-lg"],
      shadow: [
        "shadow-theme-xs",
        "shadow-theme-md",
        "shadow-theme-lg",
        "shadow-tooltip",
      ],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return customTwMerge(clsx(...inputs));
}
