import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CLUB_STATUS_BADGES, CLUB_STATUSES } from "@/lib/labels";
import type { ClubStatus } from "@/lib/types";
import type { FormEvent } from "react";

interface ClubFiltersProps {
  status: ClubStatus | null;
  search: string;
  onChange: (filters: { status: ClubStatus | null; search: string }) => void;
}

/** Status tabs and a name search for the admin's list of every club. */
export function ClubFilters({ status, search, onChange }: ClubFiltersProps) {
  const tabs: { label: string; value: ClubStatus | null }[] = [
    { label: "All", value: null },
    ...CLUB_STATUSES.map((value) => ({
      label: CLUB_STATUS_BADGES[value].label,
      value,
    })),
  ];

  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const query = new FormData(event.currentTarget).get("q");
    onChange({ status, search: typeof query === "string" ? query.trim() : "" });
  };

  return (
    <div className="flex flex-col gap-4 px-4 py-4 sm:px-6 xl:flex-row xl:items-center xl:justify-between">
      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <Button
            key={tab.label}
            size="sm"
            variant={tab.value === status ? "default" : "outline"}
            aria-pressed={tab.value === status}
            onClick={() => onChange({ status: tab.value, search })}
          >
            {tab.label}
          </Button>
        ))}
      </div>

      {/* Keyed by the search so clearing the filters also clears the box. */}
      <form
        key={search}
        role="search"
        onSubmit={submitSearch}
        className="flex gap-2 xl:w-80"
      >
        <Input
          type="search"
          name="q"
          defaultValue={search}
          placeholder="Search by club name"
          aria-label="Search clubs by name"
          className="h-9"
        />
        <Button type="submit" size="sm" variant="outline">
          Search
        </Button>
      </form>
    </div>
  );
}
