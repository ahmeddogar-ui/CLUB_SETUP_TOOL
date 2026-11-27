import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { USER_ROLE_LABELS, USER_ROLES } from "@/lib/labels";
import type { UserRole } from "@/lib/types";
import type { FormEvent } from "react";

interface UserFiltersProps {
  role: UserRole | null;
  search: string;
  onChange: (filters: { role: UserRole | null; search: string }) => void;
}

/** Role tabs and a name or email search for the admin's list of users. */
export function UserFilters({ role, search, onChange }: UserFiltersProps) {
  const tabs: { label: string; value: UserRole | null }[] = [
    { label: "All", value: null },
    ...USER_ROLES.map((value) => ({ label: USER_ROLE_LABELS[value], value })),
  ];

  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const query = new FormData(event.currentTarget).get("q");
    onChange({ role, search: typeof query === "string" ? query.trim() : "" });
  };

  return (
    <div className="flex flex-col gap-4 px-4 py-4 sm:px-6 xl:flex-row xl:items-center">
      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <Button
            key={tab.label}
            size="sm"
            variant={tab.value === role ? "default" : "outline"}
            aria-pressed={tab.value === role}
            onClick={() => onChange({ role: tab.value, search })}
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
        className="flex gap-2 xl:ml-auto xl:w-80"
      >
        <Input
          type="search"
          name="q"
          defaultValue={search}
          placeholder="Search by name or email"
          aria-label="Search users"
          className="h-9"
        />
        <Button type="submit" size="sm" variant="outline">
          Search
        </Button>
      </form>
    </div>
  );
}
