import { NativeSelect } from "@/components/shared/native-select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { XIcon } from "@/icons";
import { EVENT_LABELS, EVENT_TYPES, isEventType } from "@/lib/labels";
import type { ActivityFilters } from "./activity-query";

interface ActivityFilterBarProps {
  filters: ActivityFilters;
  onChange: (filters: ActivityFilters) => void;
  /** Chips naming the actor and club filters, shown under the fields. */
  chips: { label: string; onRemove: () => void }[];
  onClear: (() => void) | null;
}

/** The activity log's action, date range and actor/club filters. */
export function ActivityFilterBar({
  filters,
  onChange,
  chips,
  onClear,
}: ActivityFilterBarProps) {
  return (
    <div className="flex flex-col gap-4 px-4 py-4 sm:px-6">
      <div className="flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1 text-xs font-medium text-gray-500 dark:text-gray-400">
          Action
          <NativeSelect
            value={filters.eventType ?? ""}
            onChange={(event) =>
              onChange({
                ...filters,
                eventType: isEventType(event.target.value)
                  ? event.target.value
                  : null,
              })
            }
          >
            <option value="">All actions</option>
            {EVENT_TYPES.map((type) => (
              <option key={type} value={type}>
                {EVENT_LABELS[type]}
              </option>
            ))}
          </NativeSelect>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-gray-500 dark:text-gray-400">
          From
          <Input
            type="date"
            value={filters.since ?? ""}
            max={filters.until ?? undefined}
            onChange={(event) =>
              onChange({ ...filters, since: event.target.value || null })
            }
            className="h-9 w-auto"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-gray-500 dark:text-gray-400">
          To
          <Input
            type="date"
            value={filters.until ?? ""}
            min={filters.since ?? undefined}
            onChange={(event) =>
              onChange({ ...filters, until: event.target.value || null })
            }
            className="h-9 w-auto"
          />
        </label>
        {onClear && (
          <Button size="sm" variant="outline" onClick={onClear}>
            Clear filters
          </Button>
        )}
      </div>

      {chips.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {chips.map((chip) => (
            <li
              key={chip.label}
              className="inline-flex items-center gap-1 rounded-full bg-gray-100 py-1 ps-3 pe-1 text-sm text-gray-700 dark:bg-gray-800 dark:text-gray-300"
            >
              {chip.label}
              <button
                type="button"
                aria-label={`Remove filter ${chip.label}`}
                onClick={chip.onRemove}
                className="rounded-full p-1 hover:bg-gray-200 dark:hover:bg-gray-700"
              >
                <XIcon aria-hidden className="size-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
