import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { FieldErrors, UseFormRegister } from "react-hook-form";
import type { ClubFormData } from "./club-schema";

interface ClubFieldsProps {
  register: UseFormRegister<ClubFormData>;
  errors: FieldErrors<ClubFormData>;
}

export function ClubFields({ register, errors }: ClubFieldsProps) {
  return (
    <>
      <Field data-invalid={Boolean(errors.name)}>
        <FieldLabel className="mb-1.5 block">
          Club name <span className="text-red-500">*</span>
        </FieldLabel>
        <Input
          {...register("name")}
          type="text"
          placeholder="e.g. Chess Club"
          aria-invalid={errors.name ? "true" : undefined}
        />
        <FieldError errors={[errors.name]} />
      </Field>

      <Field data-invalid={Boolean(errors.description)}>
        <FieldLabel className="mb-1.5 block">
          Description <span className="text-red-500">*</span>
        </FieldLabel>
        <Textarea
          {...register("description")}
          rows={4}
          placeholder="What does your club do?"
          aria-invalid={errors.description ? "true" : undefined}
        />
        <FieldError errors={[errors.description]} />
      </Field>
    </>
  );
}
