import { cn } from "@/utils";
import type { KeyboardEvent, ReactNode } from "react";

export type ClubTab = "overview" | "requests";

const TABS: { id: ClubTab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "requests", label: "Requests" },
];

const tabId = (tab: ClubTab) => `club-tab-${tab}`;
const panelId = (tab: ClubTab) => `club-panel-${tab}`;

interface ClubTabsProps {
  selected: ClubTab;
  onSelect: (tab: ClubTab) => void;
}

/** The tablist above a club's panels. Arrow keys move between the tabs. */
export function ClubTabs({ selected, onSelect }: ClubTabsProps) {
  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    const next = TABS.find((tab) => tab.id !== selected);
    if (!next) return;
    onSelect(next.id);
    document.getElementById(tabId(next.id))?.focus();
  };

  return (
    <div
      role="tablist"
      aria-label="Club sections"
      onKeyDown={handleKeyDown}
      className="mb-6 flex gap-6 border-b border-gray-200 dark:border-gray-800"
    >
      {TABS.map((tab) => {
        const isSelected = tab.id === selected;
        return (
          <button
            key={tab.id}
            id={tabId(tab.id)}
            type="button"
            role="tab"
            aria-selected={isSelected}
            aria-controls={panelId(tab.id)}
            tabIndex={isSelected ? 0 : -1}
            onClick={() => onSelect(tab.id)}
            className={cn(
              "-mb-px border-b-2 px-1 pb-3 text-sm font-medium",
              isSelected
                ? "border-brand-500 text-brand-500 dark:border-brand-400 dark:text-brand-400"
                : "border-transparent text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-white/90",
            )}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

/** The content of the selected tab. */
export function ClubTabPanel({
  tab,
  children,
}: {
  tab: ClubTab;
  children: ReactNode;
}) {
  return (
    <div role="tabpanel" id={panelId(tab)} aria-labelledby={tabId(tab)}>
      {children}
    </div>
  );
}
