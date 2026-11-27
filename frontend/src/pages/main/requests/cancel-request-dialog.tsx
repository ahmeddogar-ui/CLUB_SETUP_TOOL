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
import { OctagonAlertIcon } from "@/icons";
import { apiFetch } from "@/lib/api";
import { useState } from "react";
import { useClubMutation } from "../clubs/use-club-mutation";

interface CancelRequestDialogProps {
  requestId: number;
  requestTitle: string;
}

/** Cancelling is final, so it asks first. */
export function CancelRequestDialog({
  requestId,
  requestTitle,
}: CancelRequestDialogProps) {
  const [isOpen, setIsOpen] = useState(false);

  const cancel = useClubMutation(
    () => apiFetch(`/requests/${requestId}/cancel`, { method: "POST" }),
    "Request cancelled",
    ["requests"],
  );

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);
    cancel.reset();
  };

  return (
    <>
      <Button variant="outline" onClick={() => handleOpenChange(true)}>
        Cancel request
      </Button>

      <Dialog open={isOpen} onOpenChange={handleOpenChange}>
        <DialogContent>
          {cancel.error && (
            <Alert variant="destructive" className="p-4">
              <OctagonAlertIcon className="size-5" />
              <AlertDescription>{cancel.error.message}</AlertDescription>
            </Alert>
          )}
          <DialogHeader>
            <DialogTitle>Cancel {requestTitle}?</DialogTitle>
            <DialogDescription>
              The request will be closed and can't be reopened.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => handleOpenChange(false)}>
              Keep request
            </Button>
            <Button
              variant="destructive"
              disabled={cancel.isPending}
              onClick={() =>
                cancel.mutate(undefined, { onSuccess: () => setIsOpen(false) })
              }
            >
              {cancel.isPending ? "Cancelling..." : "Yes, cancel request"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
