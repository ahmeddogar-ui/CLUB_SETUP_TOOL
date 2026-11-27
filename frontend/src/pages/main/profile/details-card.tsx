import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { OctagonAlertIcon } from "@/icons";
import { apiFetch } from "@/lib/api";
import { USER_ROLE_LABELS } from "@/lib/labels";
import type { User } from "@/lib/types";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { nameSchema, type NameFormData } from "./profile-schema";

export function DetailsCard({ user }: { user: User }) {
  const queryClient = useQueryClient();

  const rename = useMutation({
    mutationFn: (data: NameFormData) =>
      apiFetch<User>("/auth/me", {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    meta: { successMessage: "Name updated" },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["me"] }),
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<NameFormData>({
    resolver: zodResolver(nameSchema),
    defaultValues: { name: user.name },
    mode: "onTouched",
  });

  return (
    <Card className="rounded-2xl border border-gray-200 bg-white p-5 sm:p-6 dark:border-gray-800 dark:bg-white/3">
      <div>
        <CardTitle className="text-lg font-semibold text-gray-800 dark:text-white/90">
          Your details
        </CardTitle>
        <CardDescription>
          Your name appears on the clubs you register and in their history.
        </CardDescription>
      </div>

      <form
        onSubmit={handleSubmit((data) => rename.mutate(data))}
        className="space-y-5"
        noValidate
      >
        {rename.error && (
          <Alert variant="destructive" className="p-4">
            <OctagonAlertIcon className="size-5" />
            <AlertDescription>{rename.error.message}</AlertDescription>
          </Alert>
        )}

        <Field data-invalid={Boolean(errors.name)}>
          <FieldLabel className="mb-1.5 block">
            Name <span className="text-red-500">*</span>
          </FieldLabel>
          <Input
            {...register("name")}
            type="text"
            aria-invalid={errors.name ? "true" : undefined}
          />
          <FieldError errors={[errors.name]} />
        </Field>

        <dl className="grid grid-cols-1 gap-5 text-sm sm:grid-cols-2">
          <div>
            <dt className="mb-1.5 text-gray-500 dark:text-gray-400">Email</dt>
            <dd className="text-gray-800 dark:text-white/90">{user.email}</dd>
          </div>
          <div>
            <dt className="mb-1.5 text-gray-500 dark:text-gray-400">Role</dt>
            <dd className="text-gray-800 dark:text-white/90">
              {USER_ROLE_LABELS[user.role]}
            </dd>
          </div>
        </dl>

        <div className="flex justify-end">
          <Button type="submit" disabled={rename.isPending}>
            {rename.isPending ? "Saving..." : "Save changes"}
          </Button>
        </div>
      </form>
    </Card>
  );
}
