import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { OctagonAlertIcon } from "@/icons";
import { REQUEST_TITLE_MAX_LENGTH } from "@/lib/limits";
import { REQUEST_TYPE_LABELS } from "@/lib/request-labels";
import type { RequestInput, RequestType } from "@/lib/request-types";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, useWatch } from "react-hook-form";
import { Link } from "react-router";
import { BookingFields } from "./booking-fields";
import { FundingFields } from "./funding-fields";
import {
  requestFormSchema,
  toRequestInput,
  type RequestFormValues,
} from "./request-schema";

const TYPE_DESCRIPTIONS: Record<RequestType, string> = {
  funding: "Ask for money, itemised as line items.",
  room_booking: "Reserve a room for a date and time.",
};

interface RequestFormProps {
  defaultValues: RequestFormValues;
  /** An existing request keeps its type. */
  isTypeLocked: boolean;
  submitLabel: string;
  isPending: boolean;
  /** The backend's refusal, e.g. a double-booked room. */
  error: Error | null;
  cancelPath: string;
  onSubmit: (input: RequestInput) => void;
}

export function RequestForm({
  defaultValues,
  isTypeLocked,
  submitLabel,
  isPending,
  error,
  cancelPath,
  onSubmit,
}: RequestFormProps) {
  const form = useForm<RequestFormValues>({
    resolver: zodResolver(requestFormSchema),
    defaultValues,
    mode: "onTouched",
  });
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = form;
  const requestType = useWatch({ control, name: "request_type" });

  return (
    <Card className="max-w-2xl rounded-2xl border border-gray-200 bg-white p-5 sm:p-6 dark:border-gray-800 dark:bg-white/3">
      <form
        onSubmit={handleSubmit((values) => onSubmit(toRequestInput(values)))}
        className="space-y-5"
        noValidate
      >
        {error && (
          <Alert variant="destructive" className="p-4">
            <OctagonAlertIcon className="size-5" />
            <AlertTitle>Could not save request</AlertTitle>
            <AlertDescription>{error.message}</AlertDescription>
          </Alert>
        )}

        <fieldset disabled={isTypeLocked}>
          <legend className="mb-1.5 text-sm font-medium text-gray-800 dark:text-white/90">
            Type
          </legend>
          <div className="grid gap-3 sm:grid-cols-2">
            {(Object.keys(REQUEST_TYPE_LABELS) as RequestType[]).map((type) => (
              <label
                key={type}
                className="block cursor-pointer rounded-xl border border-gray-300 p-4 has-checked:border-brand-500 has-checked:bg-brand-50 has-disabled:cursor-not-allowed has-disabled:opacity-60 dark:border-gray-700 dark:has-checked:bg-brand-500/10"
              >
                <input
                  {...register("request_type")}
                  type="radio"
                  value={type}
                  className="sr-only"
                />
                <span className="block font-medium text-gray-800 dark:text-white/90">
                  {REQUEST_TYPE_LABELS[type]}
                </span>
                <span className="mt-1 block text-sm text-gray-500 dark:text-gray-400">
                  {TYPE_DESCRIPTIONS[type]}
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <Field data-invalid={Boolean(errors.title)}>
          <FieldLabel className="mb-1.5 block">
            Title <span className="text-red-500">*</span>
          </FieldLabel>
          <Input
            {...register("title")}
            type="text"
            maxLength={REQUEST_TITLE_MAX_LENGTH}
            aria-invalid={errors.title ? "true" : undefined}
          />
          <FieldError errors={[errors.title]} />
        </Field>

        {requestType === "funding" ? (
          <FundingFields form={form} />
        ) : (
          <BookingFields form={form} />
        )}

        <div className="flex justify-end gap-3">
          <Button
            variant="outline"
            nativeButton={false}
            render={<Link to={cancelPath} />}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={isPending}>
            {isPending ? "Saving..." : submitLabel}
          </Button>
        </div>
      </form>
    </Card>
  );
}
