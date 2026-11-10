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
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { OctagonAlertIcon } from "@/icons";
import { apiFetch } from "@/lib/api";
import { REQUIREMENT_LABELS } from "@/lib/labels";
import type { Requirement } from "@/lib/types";
import { useState } from "react";
import { useClubMutation } from "./use-club-mutation";

export function LinkDialog({ requirement }: { requirement: Requirement }) {
  const [isOpen, setIsOpen] = useState(false);
  const [linkUrl, setLinkUrl] = useState("");
  const label = REQUIREMENT_LABELS[requirement.requirement_type];

  const saveLink = useClubMutation((link_url: string) =>
    apiFetch(
      `/clubs/${requirement.club_id}/requirements/${requirement.requirement_type}/link`,
      { method: "PUT", body: JSON.stringify({ link_url }) },
    ),
  );

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);
    setLinkUrl(requirement.link_url ?? "");
    saveLink.reset();
  };

  const handleSave = () =>
    saveLink.mutate(linkUrl.trim(), { onSuccess: () => setIsOpen(false) });

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

          {saveLink.error && (
            <Alert variant="destructive" className="p-4">
              <OctagonAlertIcon className="size-5" />
              <AlertDescription>{saveLink.error.message}</AlertDescription>
            </Alert>
          )}

          <Field>
            <FieldLabel className="mb-1.5 block">
              Document link <span className="text-red-500">*</span>
            </FieldLabel>
            <Input
              type="url"
              value={linkUrl}
              onChange={(event) => setLinkUrl(event.target.value)}
              placeholder="https://"
            />
          </Field>

          <DialogFooter>
            <Button variant="outline" onClick={() => handleOpenChange(false)}>
              Cancel
            </Button>
            <Button
              disabled={saveLink.isPending || !linkUrl.trim()}
              onClick={handleSave}
            >
              {saveLink.isPending ? "Saving..." : "Save link"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
