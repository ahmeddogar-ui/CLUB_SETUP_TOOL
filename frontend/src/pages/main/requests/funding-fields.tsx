import { Button } from "@/components/ui/button";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { PlusIcon, XIcon } from "@/icons";
import { LINE_ITEM_DESCRIPTION_MAX_LENGTH, MAX_LINE_ITEMS } from "@/lib/limits";
import { formatCents } from "@/lib/request-labels";
import {
  useFieldArray,
  useFormState,
  useWatch,
  type UseFormReturn,
} from "react-hook-form";
import { parseAmountCents, type RequestFormValues } from "./request-schema";

const EMPTY_LINE_ITEM = { description: "", amount: "" };

export function FundingFields({
  form,
}: {
  form: UseFormReturn<RequestFormValues>;
}) {
  const { control, register } = form;
  const { errors } = useFormState({ control });
  const { fields, append, remove } = useFieldArray({
    control,
    name: "line_items",
  });
  const lineItems = useWatch({ control, name: "line_items" });

  // An amount that isn't valid yet counts as nothing, until it's corrected.
  const totalCents = lineItems.reduce(
    (sum, item) => sum + (parseAmountCents(item.amount) ?? 0),
    0,
  );

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium text-gray-800 dark:text-white/90">
        Line items
      </h3>

      {fields.map((field, index) => {
        const itemErrors = errors.line_items?.[index];
        return (
          <div
            key={field.id}
            className="grid grid-cols-[1fr_auto] gap-3 sm:grid-cols-[1fr_10rem_auto]"
          >
            <Field data-invalid={Boolean(itemErrors?.description)}>
              <FieldLabel className="mb-1.5 block">Description</FieldLabel>
              <Input
                {...register(`line_items.${index}.description`)}
                type="text"
                maxLength={LINE_ITEM_DESCRIPTION_MAX_LENGTH}
                aria-invalid={itemErrors?.description ? "true" : undefined}
              />
              <FieldError errors={[itemErrors?.description]} />
            </Field>

            <Field
              data-invalid={Boolean(itemErrors?.amount)}
              className="col-start-1 sm:col-start-auto"
            >
              <FieldLabel className="mb-1.5 block">Amount (CAD)</FieldLabel>
              <Input
                {...register(`line_items.${index}.amount`)}
                type="text"
                inputMode="decimal"
                placeholder="125.50"
                aria-invalid={itemErrors?.amount ? "true" : undefined}
              />
              <FieldError errors={[itemErrors?.amount]} />
            </Field>

            <Button
              type="button"
              variant="outline"
              size="icon"
              aria-label={`Remove line item ${index + 1}`}
              disabled={fields.length === 1}
              onClick={() => remove(index)}
              className="col-start-2 row-start-1 mt-7 sm:col-start-auto sm:row-start-auto"
            >
              <XIcon />
            </Button>
          </div>
        );
      })}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={fields.length >= MAX_LINE_ITEMS}
          onClick={() => append(EMPTY_LINE_ITEM)}
        >
          <PlusIcon /> Add line item
        </Button>
        <p className="text-sm font-medium text-gray-800 dark:text-white/90">
          Total{" "}
          <output className="ms-2 text-base">{formatCents(totalCents)}</output>
        </p>
      </div>
    </div>
  );
}
