import { Alert, AlertDescription } from "@/components/ui/alert";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { OctagonAlertIcon } from "@/icons";
import { apiFetch } from "@/lib/api";
import type { Room } from "@/lib/request-types";
import { useQuery } from "@tanstack/react-query";
import { useFormState, type UseFormReturn } from "react-hook-form";
import type { RequestFormValues } from "./request-schema";

const ROOM_SELECT_ID = "request-room";
const SELECT_CLASS =
  "h-11 w-full rounded-[10px] border border-gray-300 bg-white px-4 text-sm text-gray-800 shadow-theme-xs outline-hidden focus:border-brand-300 focus:ring-3 focus:ring-brand-500/20 aria-invalid:border-red-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

export function BookingFields({
  form,
}: {
  form: UseFormReturn<RequestFormValues>;
}) {
  const { control, register } = form;
  const { errors } = useFormState({ control });
  const rooms = useQuery({
    queryKey: ["rooms"],
    queryFn: () => apiFetch<Room[]>("/rooms"),
  });

  return (
    <div className="space-y-5">
      {rooms.error && (
        <Alert variant="destructive" className="p-4">
          <OctagonAlertIcon className="size-5" />
          <AlertDescription>
            Could not load rooms: {rooms.error.message}
          </AlertDescription>
        </Alert>
      )}

      <Field data-invalid={Boolean(errors.room_id)}>
        <FieldLabel htmlFor={ROOM_SELECT_ID} className="mb-1.5 block">
          Room <span className="text-red-500">*</span>
        </FieldLabel>
        <select
          {...register("room_id")}
          id={ROOM_SELECT_ID}
          className={SELECT_CLASS}
          aria-invalid={errors.room_id ? "true" : undefined}
        >
          <option value="">Choose a room</option>
          {rooms.data?.map((room) => (
            <option key={room.id} value={room.id}>
              {room.name} — {room.building} ({room.capacity})
            </option>
          ))}
        </select>
        <FieldError errors={[errors.room_id]} />
      </Field>

      <Field data-invalid={Boolean(errors.date)}>
        <FieldLabel className="mb-1.5 block">
          Date <span className="text-red-500">*</span>
        </FieldLabel>
        <Input
          {...register("date")}
          type="date"
          aria-invalid={errors.date ? "true" : undefined}
        />
        <FieldError errors={[errors.date]} />
      </Field>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field data-invalid={Boolean(errors.start_time)}>
          <FieldLabel className="mb-1.5 block">
            Start time <span className="text-red-500">*</span>
          </FieldLabel>
          <Input
            {...register("start_time")}
            type="time"
            aria-invalid={errors.start_time ? "true" : undefined}
          />
          <FieldError errors={[errors.start_time]} />
        </Field>

        <Field data-invalid={Boolean(errors.end_time)}>
          <FieldLabel className="mb-1.5 block">
            End time <span className="text-red-500">*</span>
          </FieldLabel>
          <Input
            {...register("end_time")}
            type="time"
            aria-invalid={errors.end_time ? "true" : undefined}
          />
          <FieldError errors={[errors.end_time]} />
        </Field>
      </div>
    </div>
  );
}
