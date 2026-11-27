import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { OctagonAlertIcon } from "@/icons";
import { apiFetch } from "@/lib/api";
import { REQUIREMENT_LABELS } from "@/lib/labels";
import type { Requirement } from "@/lib/types";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useClubMutation } from "./use-club-mutation";

const INVALID_LINK = "Enter a full link, starting with https://";

// The backend accepts http(s) URLs only (AnyHttpUrl).
const linkSchema = z.object({
  link_url: z
    .string()
    .trim()
    .url(INVALID_LINK)
    .refine((url) => /^https?:\/\//i.test(url), INVALID_LINK),
});

type LinkFormData = z.infer<typeof linkSchema>;

export function LinkDialog({ requirement }: { requirement: Requirement }) {
  const [isOpen, setIsOpen] = useState(false);
  const label = REQUIREMENT_LABELS[requirement.requirement_type];

  const saveLink = useClubMutation(
    (data: LinkFormData) =>
      apiFetch(
        `/clubs/${requirement.club_id}/requirements/${requirement.requirement_type}/link`,
        { method: "PUT", body: JSON.stringify(data) },
      ),
    "Link saved",
  );

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<LinkFormData>({
    resolver: zodResolver(linkSchema),
    mode: "onTouched",
  });

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);
    reset({ link_url: requirement.link_url ?? "" });
    saveLink.reset();
  };

  const handleSave = (data: LinkFormData) =>
    saveLink.mutate(data, { onSuccess: () => setIsOpen(false) });

  return (
    <>
      <Button
        size="xs"
        variant="outline"
        onClick={() => handleOpenChange(true)}
      >
        {requirement.link_url ? "Replace link" : "Provide link"}
      </Button>

      <Dialog open={isOpen} onOpenChange={handleOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{label}</DialogTitle>
            <DialogDescription>
              Paste a shareable link to the document (for example a Google Drive
              or OneDrive link).
            </DialogDescription>
          </DialogHeader>

          {/* A real form, so Enter in the field saves. */}
          <form
            onSubmit={handleSubmit(handleSave)}
            className="space-y-5"
            noValidate
          >
            {saveLink.error && (
              <Alert variant="destructive" className="p-4">
                <OctagonAlertIcon className="size-5" />
                <AlertDescription>{saveLink.error.message}</AlertDescription>
              </Alert>
            )}

            <Field data-invalid={Boolean(errors.link_url)}>
              <FieldLabel className="mb-1.5 block">
                Document link <span className="text-red-500">*</span>
              </FieldLabel>
              <Input
                {...register("link_url")}
                type="url"
                placeholder="https://"
                aria-invalid={errors.link_url ? "true" : undefined}
              />
              <FieldError errors={[errors.link_url]} />
            </Field>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => handleOpenChange(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={saveLink.isPending}>
                {saveLink.isPending ? "Saving..." : "Save link"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
