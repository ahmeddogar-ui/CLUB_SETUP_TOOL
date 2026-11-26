import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import type { Club } from "@/lib/types";
import { NoteActionDialog } from "./note-action-dialog";
import { toast } from "sonner";
import { useClubMutation } from "./use-club-mutation";

interface ClubActionsProps {
  club: Club;
  canSubmit: boolean;
  isAdmin: boolean;
}

export function ClubActions({ club, canSubmit, isAdmin }: ClubActionsProps) {
  const clubPath = `/clubs/${club.id}`;
  const isResubmit = club.status === "changes_requested";
  const isAwaitingReview = club.status === "submitted";
  const isUnderReview = club.status === "under_review";
  const hasActions =
    canSubmit || (isAdmin && (isAwaitingReview || isUnderReview));

  if (!hasActions) return null;

  return (
    <div className="mt-4 flex flex-wrap gap-3">
      {canSubmit &&
        (isResubmit ? (
          <ActionButton
            path={`${clubPath}/resubmit`}
            label="Resubmit for review"
            successMessage="Club resubmitted for review"
          />
        ) : (
          <ActionButton
            path={`${clubPath}/submit`}
            label="Submit for review"
            successMessage="Club submitted for review"
          />
        ))}

      {isAdmin && isAwaitingReview && (
        <ActionButton
          path={`${clubPath}/start-review`}
          label="Start review"
          successMessage="Review started"
        />
      )}

      {isAdmin && isUnderReview && (
        <>
          <ActionButton
            path={`${clubPath}/approve`}
            label="Approve club"
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
  );
}

interface ActionButtonProps {
  path: string;
  label: string;
  successMessage: string;
}

/** A one-click action. With no dialog to hold an error, a refusal (such as
 * "missing: budget") is shown as an error toast. */
function ActionButton({ path, label, successMessage }: ActionButtonProps) {
  const action = useClubMutation(
    () => apiFetch(path, { method: "POST" }),
    successMessage,
  );

  return (
    <Button
      disabled={action.isPending}
      onClick={() =>
        action.mutate(undefined, {
          onError: (error) => toast.error(error.message),
        })
      }
    >
      {label}
    </Button>
  );
}
