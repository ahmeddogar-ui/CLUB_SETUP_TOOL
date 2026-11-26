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
import { NOTE_MAX_LENGTH } from "@/lib/limits";
import { OctagonAlertIcon } from "@/icons";
import { apiFetch } from "@/lib/api";
import { useState } from "react";
import { useClubMutation } from "./use-club-mutation";

/** A second step for actions that are hard to take back. */
export interface Confirmation {
  title: string;
  confirmLabel: string;
}

interface NoteActionDialogProps {
  actionPath: string;
  title: string;
  description: string;
  triggerLabel: string;
  successMessage: string;
  isNoteRequired: boolean;
  confirmation?: Confirmation;
  variant?: "default" | "outline" | "destructive";
  size?: "xs" | "sm";
}

export function NoteActionDialog({
  actionPath,
  title,
  description,
  triggerLabel,
  successMessage,
  isNoteRequired,
  confirmation,
  variant = "default",
  size = "sm",
}: NoteActionDialogProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [note, setNote] = useState("");

  const action = useClubMutation(
    (trimmedNote: string) =>
      apiFetch(actionPath, {
        method: "POST",
        body: JSON.stringify({ note: trimmedNote || null }),
      }),
    successMessage,
  );

  const trimmedNote = note.trim();
  const canSend = !action.isPending && (!isNoteRequired || trimmedNote);
  const confirmVariant = variant === "destructive" ? "destructive" : "default";

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);
    setIsConfirming(false);
    setNote("");
    action.reset();
  };

  const send = () =>
    action.mutate(trimmedNote, { onSuccess: () => setIsOpen(false) });

  const handlePrimary = () => (confirmation ? setIsConfirming(true) : send());

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
          {action.error && (
            <Alert variant="destructive" className="p-4">
              <OctagonAlertIcon className="size-5" />
              <AlertDescription>{action.error.message}</AlertDescription>
            </Alert>
          )}

          {isConfirming && confirmation ? (
            <>
              <DialogHeader>
                <DialogTitle>{confirmation.title}</DialogTitle>
                <DialogDescription>{description}</DialogDescription>
              </DialogHeader>
              <blockquote className="rounded-lg border border-gray-200 bg-gray-50 p-3 whitespace-pre-line text-gray-700 dark:border-gray-800 dark:bg-white/3 dark:text-gray-300">
                {trimmedNote}
              </blockquote>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setIsConfirming(false)}
                >
                  Back
                </Button>
                <Button
                  variant={confirmVariant}
                  disabled={action.isPending}
                  onClick={send}
                >
                  {action.isPending ? "Saving..." : confirmation.confirmLabel}
                </Button>
              </DialogFooter>
            </>
          ) : (
            <>
              <DialogHeader>
                <DialogTitle>{title}</DialogTitle>
                <DialogDescription>{description}</DialogDescription>
              </DialogHeader>
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
                  // Back from the confirmation returns focus to the note.
                  autoFocus={Boolean(trimmedNote)}
                  rows={4}
                  maxLength={NOTE_MAX_LENGTH}
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="Explain your decision"
                />
              </Field>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => handleOpenChange(false)}
                >
                  Cancel
                </Button>
                <Button
                  variant={confirmVariant}
                  disabled={!canSend}
                  onClick={handlePrimary}
                >
                  {action.isPending ? "Saving..." : triggerLabel}
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
