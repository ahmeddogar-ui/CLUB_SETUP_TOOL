import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { OctagonAlertIcon, PencilIcon } from "@/icons";
import { apiFetch } from "@/lib/api";
import type { Club } from "@/lib/types";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { ClubFields } from "./club-fields";
import { clubSchema, type ClubFormData } from "./club-schema";
import { useClubMutation } from "./use-club-mutation";

export function EditClubDialog({ club }: { club: Club }) {
  const [isOpen, setIsOpen] = useState(false);

  const updateClub = useClubMutation((data: ClubFormData) =>
    apiFetch(`/clubs/${club.id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  );

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ClubFormData>({
    resolver: zodResolver(clubSchema),
    mode: "onTouched",
  });

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);
    reset({ name: club.name, description: club.description });
    updateClub.reset();
  };

  const handleSave = (data: ClubFormData) =>
    updateClub.mutate(data, { onSuccess: () => setIsOpen(false) });

  return (
    <>
      <Button
        size="sm"
        variant="outline"
        onClick={() => handleOpenChange(true)}
      >
        <PencilIcon className="size-5" />
        Edit
      </Button>

      <Dialog open={isOpen} onOpenChange={handleOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit club</DialogTitle>
          </DialogHeader>

          <form
            onSubmit={handleSubmit(handleSave)}
            className="space-y-5"
            noValidate
          >
            {updateClub.error && (
              <Alert variant="destructive" className="p-4">
                <OctagonAlertIcon className="size-5" />
                <AlertDescription>{updateClub.error.message}</AlertDescription>
              </Alert>
            )}

            <ClubFields register={register} errors={errors} />

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => handleOpenChange(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={updateClub.isPending}>
                {updateClub.isPending ? "Saving..." : "Save changes"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
