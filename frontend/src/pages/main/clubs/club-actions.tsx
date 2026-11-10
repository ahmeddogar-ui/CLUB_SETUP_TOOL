import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { OctagonAlertIcon } from "@/icons";
import { apiFetch } from "@/lib/api";
import type { Club } from "@/lib/types";
import { NoteActionDialog } from "./note-action-dialog";
import { useClubMutation } from "./use-club-mutation";

interface ClubActionsProps {
  club: Club;
  canSubmit: boolean;
  isAdmin: boolean;
}

export function ClubActions({ club, canSubmit, isAdmin }: ClubActionsProps) {
  const clubPath = `/clubs/${club.id}`;

  const postAction = useClubMutation((action: string) =>
    apiFetch(`${clubPath}/${action}`, { method: "POST" }),
  );

  const isResubmit = club.status === "changes_requested";
  const isAwaitingReview = club.status === "submitted";
  const isUnderReview = club.status === "under_review";
  const hasActions =
    canSubmit || (isAdmin && (isAwaitingReview || isUnderReview));

  if (!hasActions) return null;

  return (
    <div className="space-y-4">
      {postAction.error && (
        <Alert variant="destructive" className="p-4">
          <OctagonAlertIcon className="size-5" />
          <AlertTitle>Action failed</AlertTitle>
          <AlertDescription>{postAction.error.message}</AlertDescription>
        </Alert>
      )}

      <div className="flex flex-wrap gap-3">
        {canSubmit && (
          <Button
            disabled={postAction.isPending}
            onClick={() =>
              postAction.mutate(isResubmit ? "resubmit" : "submit")
            }
          >
            {isResubmit ? "Resubmit for review" : "Submit for review"}
          </Button>
        )}

        {isAdmin && isAwaitingReview && (
          <Button
            disabled={postAction.isPending}
            onClick={() => postAction.mutate("start-review")}
          >
            Start review
          </Button>
        )}

        {isAdmin && isUnderReview && (
          <>
            <Button
              disabled={postAction.isPending}
              onClick={() => postAction.mutate("approve")}
            >
              Approve club
            </Button>
            <NoteActionDialog
              actionPath={`${clubPath}/request-changes`}
              title="Request changes"
              description="The club lead will see this note and can resubmit."
              triggerLabel="Request changes"
              isNoteRequired
              variant="outline"
            />
            <NoteActionDialog
              actionPath={`${clubPath}/reject`}
              title="Reject club"
              description="This is final. The club cannot be resubmitted."
              triggerLabel="Reject club"
              isNoteRequired
              variant="destructive"
            />
          </>
        )}
      </div>
    </div>
  );
}
