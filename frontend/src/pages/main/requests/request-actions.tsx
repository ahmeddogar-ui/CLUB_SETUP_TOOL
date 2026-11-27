import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { OctagonAlertIcon } from "@/icons";
import { apiFetch } from "@/lib/api";
import type { RequestAction, RequestDetail } from "@/lib/request-types";
import { Fragment, useState } from "react";
import { NoteActionDialog } from "../clubs/note-action-dialog";
import { useClubMutation } from "../clubs/use-club-mutation";
import { CancelRequestDialog } from "./cancel-request-dialog";

const REQUESTS_KEY = ["requests"];

interface RequestActionsProps {
  request: RequestDetail;
}

/** One button per action the backend allows the signed-in user right now. */
export function RequestActions({ request }: RequestActionsProps) {
  // Shown inline, not as a toast: a refusal such as a double-booked room is
  // what the lead works from while fixing the request.
  const [error, setError] = useState<Error | null>(null);
  const requestPath = `/requests/${request.id}`;
  const actionProps = { onStart: () => setError(null), onError: setError };

  const renderAction = (action: RequestAction) => {
    switch (action) {
      case "submit":
        return (
          <ActionButton
            path={`${requestPath}/submit`}
            label={
              request.status === "changes_requested"
                ? "Resubmit"
                : "Submit for review"
            }
            successMessage="Request submitted for review"
            {...actionProps}
          />
        );
      case "start_review":
        return (
          <ActionButton
            path={`${requestPath}/start-review`}
            label="Start review"
            successMessage="Review started"
            {...actionProps}
          />
        );
      case "approve":
        return (
          <NoteActionDialog
            actionPath={`${requestPath}/approve`}
            title="Approve request"
            description="The club lead will see your note, if you add one."
            triggerLabel="Approve"
            successMessage="Approval recorded"
            queryKey={REQUESTS_KEY}
            isNoteRequired={false}
          />
        );
      case "request_changes":
        return (
          <NoteActionDialog
            actionPath={`${requestPath}/request-changes`}
            title="Request changes"
            description="The club lead will see this note and can resubmit."
            triggerLabel="Request changes"
            successMessage="Changes requested"
            queryKey={REQUESTS_KEY}
            isNoteRequired
            confirmation={{
              title: `Request changes to ${request.title}?`,
              confirmLabel: "Yes, request changes",
            }}
            variant="outline"
          />
        );
      case "reject":
        return (
          <NoteActionDialog
            actionPath={`${requestPath}/reject`}
            title="Reject request"
            description="The club lead will see this note."
            triggerLabel="Reject"
            successMessage="Request rejected"
            queryKey={REQUESTS_KEY}
            isNoteRequired
            confirmation={{
              title: `Reject ${request.title}?`,
              confirmLabel: "Yes, reject",
            }}
            variant="destructive"
          />
        );
      case "cancel":
        return (
          <CancelRequestDialog
            requestId={request.id}
            requestTitle={request.title}
          />
        );
    }
  };

  if (request.allowed_actions.length === 0) return null;

  return (
    <div className="mt-4 space-y-4">
      {error && (
        <Alert variant="destructive" className="p-4">
          <OctagonAlertIcon className="size-5" />
          <AlertTitle>Action failed</AlertTitle>
          <AlertDescription>{error.message}</AlertDescription>
        </Alert>
      )}
      <div className="flex flex-wrap gap-3">
        {request.allowed_actions.map((action) => (
          <Fragment key={action}>{renderAction(action)}</Fragment>
        ))}
      </div>
    </div>
  );
}

interface ActionButtonProps {
  path: string;
  label: string;
  successMessage: string;
  onStart: () => void;
  onError: (error: Error) => void;
}

function ActionButton({
  path,
  label,
  successMessage,
  onStart,
  onError,
}: ActionButtonProps) {
  const action = useClubMutation(
    () => apiFetch(path, { method: "POST" }),
    successMessage,
    REQUESTS_KEY,
  );

  return (
    <Button
      disabled={action.isPending}
      onClick={() => {
        onStart();
        action.mutate(undefined, { onError });
      }}
    >
      {label}
    </Button>
  );
}
