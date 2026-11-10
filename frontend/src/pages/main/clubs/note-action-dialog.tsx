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
import { Textarea } from "@/components/ui/textarea";
import { OctagonAlertIcon } from "@/icons";
import { apiFetch } from "@/lib/api";
import { useState } from "react";
import { useClubMutation } from "./use-club-mutation";

interface NoteActionDialogProps {
  actionPath: string;
  title: string;
  description: string;
  triggerLabel: string;
  isNoteRequired: boolean;
  variant?: "default" | "outline" | "destructive";
  size?: "xs" | "sm";
}

export function NoteActionDialog({
  actionPath,
  title,
  description,
  triggerLabel,
  isNoteRequired,
  variant = "default",
  size = "sm",
}: NoteActionDialogProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [note, setNote] = useState("");

  const action = useClubMutation((trimmedNote: string) =>
    apiFetch(actionPath, {
      method: "POST",
      body: JSON.stringify({ note: trimmedNote || null }),
    }),
  );

  const trimmedNote = note.trim();
  const canConfirm = !action.isPending && (!isNoteRequired || trimmedNote);

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);
    setNote("");
    action.reset();
  };

  const handleConfirm = () =>
    action.mutate(trimmedNote, { onSuccess: () => setIsOpen(false) });

  return (
    <>
      <Button
        variant={variant}
        size={size}
        onClick={() => handleOpenChange(true)}
      >
        {triggerLabel}
      </Button>

      <Dialog open={isOpen} onOpenChange={handleOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
            <DialogDescription>{description}</DialogDescription>
          </DialogHeader>

          {action.error && (
            <Alert variant="destructive" className="p-4">
              <OctagonAlertIcon className="size-5" />
              <AlertDescription>{action.error.message}</AlertDescription>
            </Alert>
          )}

          <Field>
            <FieldLabel className="mb-1.5 block">
              Note{" "}
              {isNoteRequired ? (
                <span className="text-red-500">*</span>
              ) : (
                <span className="text-gray-400">(optional)</span>
              )}
            </FieldLabel>
            <Textarea
              rows={4}
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Explain your decision"
            />
          </Field>

          <DialogFooter>
            <Button variant="outline" onClick={() => handleOpenChange(false)}>
              Cancel
            </Button>
            <Button
              variant={variant === "destructive" ? "destructive" : "default"}
              disabled={!canConfirm}
              onClick={handleConfirm}
            >
              {action.isPending ? "Saving..." : triggerLabel}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
