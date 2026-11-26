import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { OctagonAlertIcon } from "@/icons";
import { apiFetch } from "@/lib/api";
import type { Club } from "@/lib/types";
import { NoteActionDialog } from "./note-action-dialog";
import { useState } from "react";
import { useClubMutation } from "./use-club-mutation";

interface ClubActionsProps {
  club: Club;
  canSubmit: boolean;
  isAdmin: boolean;
}

export function ClubActions({ club, canSubmit, isAdmin }: ClubActionsProps) {
  // Shown inline, not as a toast: a refusal such as "missing: budget" is what
  // the lead works from while fixing the club.
  const [error, setError] = useState<Error | null>(null);
  const clubPath = `/clubs/${club.id}`;
  const isResubmit = club.status === "changes_requested";
  const isAwaitingReview = club.status === "submitted";
  const isUnderReview = club.status === "under_review";
  const hasActions =
    canSubmit || (isAdmin && (isAwaitingReview || isUnderReview));

  if (!hasActions) return null;

  const actionProps = { onStart: () => setError(null), onError: setError };

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
        {canSubmit &&
          (isResubmit ? (
            <ActionButton
              path={`${clubPath}/resubmit`}
              label="Resubmit for review"
              {...actionProps}
              {...actionProps}
              successMessage="Club resubmitted for review"
            />
          ) : (
            <ActionButton
              path={`${clubPath}/submit`}
              label="Submit for review"
              {...actionProps}
              {...actionProps}
              successMessage="Club submitted for review"
            />
          ))}

        {isAdmin && isAwaitingReview && (
          <ActionButton
            path={`${clubPath}/start-review`}
            label="Start review"
            {...actionProps}
            successMessage="Review started"
          />
        )}

        {isAdmin && isUnderReview && (
          <>
            <ActionButton
              path={`${clubPath}/approve`}
              label="Approve club"
              {...actionProps}
              {...actionProps}
              successMessage="Club approved"
            />
            <NoteActionDialog
              actionPath={`${clubPath}/request-changes`}
              title="Request changes"
              description="The club lead will see this note and can resubmit."
              triggerLabel="Request changes"
              successMessage="Changes requested"
              isNoteRequired
              confirmation={{
                title: `Request changes to ${club.name}?`,
                confirmLabel: "Yes, request changes",
              }}
              variant="outline"
            />
            <NoteActionDialog
              actionPath={`${clubPath}/reject`}
              title="Reject club"
              description="This is final. The club cannot be resubmitted."
              triggerLabel="Reject club"
              successMessage="Club rejected"
              isNoteRequired
              confirmation={{
                title: `Reject ${club.name}?`,
                confirmLabel: "Yes, reject",
              }}
              variant="destructive"
            />
          </>
        )}
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
