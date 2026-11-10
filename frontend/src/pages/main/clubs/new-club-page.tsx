import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { OctagonAlertIcon } from "@/icons";
import { apiFetch } from "@/lib/api";
import type { Club } from "@/lib/types";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router";
import { ClubFields } from "./club-fields";
import { clubSchema, type ClubFormData } from "./club-schema";

export default function NewClubPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const createClub = useMutation({
    mutationFn: (data: ClubFormData) =>
      apiFetch<Club>("/clubs", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: (club) => {
      void queryClient.invalidateQueries({ queryKey: ["clubs"] });
      void navigate(`/clubs/${club.id}`);
    },
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ClubFormData>({
    resolver: zodResolver(clubSchema),
    defaultValues: { name: "", description: "" },
    mode: "onTouched",
  });

  return (
    <div>
      <PageMeta
        title="New club | Club Setup"
        description="Register a new club"
      />
      <PageBreadcrumb pageTitle="New club" />

      <Card className="max-w-2xl rounded-2xl border border-gray-200 bg-white p-5 sm:p-6 dark:border-gray-800 dark:bg-white/3">
        <form
          onSubmit={handleSubmit((data) => createClub.mutate(data))}
          className="space-y-5"
          noValidate
        >
          {createClub.error && (
            <Alert variant="destructive" className="p-4">
              <OctagonAlertIcon className="size-5" />
              <AlertTitle>Could not create club</AlertTitle>
              <AlertDescription>{createClub.error.message}</AlertDescription>
            </Alert>
          )}

          <ClubFields register={register} errors={errors} />

          <div className="flex justify-end gap-3">
            <Button
              variant="outline"
              nativeButton={false}
              render={<Link to="/" />}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createClub.isPending}>
              {createClub.isPending ? "Creating..." : "Create club"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
