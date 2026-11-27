import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { OctagonAlertIcon } from "@/icons";
import { apiFetch } from "@/lib/api";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { passwordSchema, type PasswordFormData } from "./profile-schema";

const EMPTY_FORM: PasswordFormData = {
  currentPassword: "",
  newPassword: "",
  confirmPassword: "",
};

export function PasswordCard() {
  const changePassword = useMutation({
    mutationFn: (data: PasswordFormData) =>
      apiFetch("/auth/me/password", {
        method: "POST",
        body: JSON.stringify({
          current_password: data.currentPassword,
          new_password: data.newPassword,
        }),
      }),
    meta: { successMessage: "Password changed" },
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PasswordFormData>({
    resolver: zodResolver(passwordSchema),
    defaultValues: EMPTY_FORM,
    mode: "onTouched",
  });

  const handleChange = (data: PasswordFormData) =>
    changePassword.mutate(data, { onSuccess: () => reset() });

  return (
    <Card className="rounded-2xl border border-gray-200 bg-white p-5 sm:p-6 dark:border-gray-800 dark:bg-white/3">
      <div>
        <CardTitle className="text-lg font-semibold text-gray-800 dark:text-white/90">
          Change password
        </CardTitle>
        <CardDescription>
          You stay signed in here; your other sessions are signed out.
        </CardDescription>
      </div>

      <form
        onSubmit={handleSubmit(handleChange)}
        className="space-y-5"
        noValidate
      >
        {changePassword.error && (
          <Alert variant="destructive" className="p-4">
            <OctagonAlertIcon className="size-5" />
            <AlertDescription>{changePassword.error.message}</AlertDescription>
          </Alert>
        )}

        <Field data-invalid={Boolean(errors.currentPassword)}>
          <FieldLabel className="mb-1.5 block">
            Current password <span className="text-red-500">*</span>
          </FieldLabel>
          <Input
            {...register("currentPassword")}
            type="password"
            autoComplete="current-password"
            aria-invalid={errors.currentPassword ? "true" : undefined}
          />
          <FieldError errors={[errors.currentPassword]} />
        </Field>

        <Field data-invalid={Boolean(errors.newPassword)}>
          <FieldLabel className="mb-1.5 block">
            New password <span className="text-red-500">*</span>
          </FieldLabel>
          <Input
            {...register("newPassword")}
            type="password"
            autoComplete="new-password"
            aria-invalid={errors.newPassword ? "true" : undefined}
          />
          <FieldError errors={[errors.newPassword]} />
        </Field>

        <Field data-invalid={Boolean(errors.confirmPassword)}>
          <FieldLabel className="mb-1.5 block">
            Confirm new password <span className="text-red-500">*</span>
          </FieldLabel>
          <Input
            {...register("confirmPassword")}
            type="password"
            autoComplete="new-password"
            aria-invalid={errors.confirmPassword ? "true" : undefined}
          />
          <FieldError errors={[errors.confirmPassword]} />
        </Field>

        <div className="flex justify-end">
          <Button type="submit" disabled={changePassword.isPending}>
            {changePassword.isPending ? "Changing..." : "Change password"}
          </Button>
        </div>
      </form>
    </Card>
  );
}
