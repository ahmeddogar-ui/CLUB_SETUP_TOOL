import { Card, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { REQUIREMENT_LABELS } from "@/lib/labels";
import type { Requirement } from "@/lib/types";
import { LinkDialog } from "./link-dialog";
import { NoteActionDialog } from "./note-action-dialog";
import { RequirementStatusBadge } from "./status-badge";

const HEADER_CELL_CLASS =
  "px-6 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400";

interface RequirementsCardProps {
  requirements: Requirement[];
  canEditLinks: boolean;
  canReview: boolean;
}

const isReadyToApprove = (requirement: Requirement) =>
  requirement.status !== "approved" &&
  (requirement.kind === "checklist" || requirement.status === "submitted");

export function RequirementsCard({
  requirements,
  canEditLinks,
  canReview,
}: RequirementsCardProps) {
  const showActions = canEditLinks || canReview;

  return (
    <Card className="w-full gap-0 overflow-hidden rounded-2xl border border-gray-200 bg-white p-0 sm:p-0 dark:border-gray-800 dark:bg-white/3">
      <div className="px-4 py-4 sm:px-6">
        <CardTitle className="text-lg font-semibold text-gray-800 dark:text-white/90">
          Requirements
        </CardTitle>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Documents are provided as links. Checklist items are verified by the
          reviewer.
        </p>
      </div>

      <div className="max-w-full overflow-x-auto">
        <Table>
          <TableHeader className="border-y border-gray-100 bg-gray-50 dark:border-gray-800 dark:bg-gray-900">
            <TableRow>
              <TableCell isHeader className={HEADER_CELL_CLASS}>
                Requirement
              </TableCell>
              <TableCell isHeader className={HEADER_CELL_CLASS}>
                Status
              </TableCell>
              <TableCell isHeader className={HEADER_CELL_CLASS}>
                Document
              </TableCell>
              {showActions && (
                <TableCell isHeader className={HEADER_CELL_CLASS}>
                  Actions
                </TableCell>
              )}
            </TableRow>
          </TableHeader>

          <TableBody className="divide-y divide-gray-100 dark:divide-gray-800">
            {requirements.map((requirement) => {
              const label = REQUIREMENT_LABELS[requirement.requirement_type];
              const isDocument = requirement.kind === "document";
              const reviewPath = `/clubs/${requirement.club_id}/requirements/${requirement.requirement_type}`;

              return (
                <TableRow key={requirement.id}>
                  <TableCell className="px-6 py-4 text-start">
                    <span className="block text-sm font-medium text-gray-800 dark:text-white/90">
                      {label}
                    </span>
                    {requirement.reviewer_note && (
                      <span className="mt-1 block text-sm text-gray-500 dark:text-gray-400">
                        Reviewer: {requirement.reviewer_note}
                      </span>
                    )}
                  </TableCell>

                  <TableCell className="px-6 py-4 text-start">
                    <RequirementStatusBadge status={requirement.status} />
                  </TableCell>

                  <TableCell className="max-w-xs truncate px-6 py-4 text-start text-sm">
                    {!isDocument ? (
                      <span className="text-gray-500 dark:text-gray-400">
                        Checked by reviewer
                      </span>
                    ) : requirement.link_url ? (
                      <a
                        href={requirement.link_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-brand-500 hover:text-brand-600 dark:text-brand-400"
                      >
                        {requirement.link_url}
                      </a>
                    ) : (
                      <span className="text-gray-400">Not provided</span>
                    )}
                  </TableCell>

                  {showActions && (
                    <TableCell className="px-6 py-4 text-start">
                      <div className="flex gap-2">
                        {canEditLinks && isDocument && (
                          <LinkDialog requirement={requirement} />
                        )}
                        {canReview && isReadyToApprove(requirement) && (
                          <NoteActionDialog
                            actionPath={`${reviewPath}/approve`}
                            title={`Approve ${label}`}
                            description="Optionally leave a note for the club."
                            triggerLabel="Approve"
                            isNoteRequired={false}
                            size="xs"
                          />
                        )}
                        {canReview && (
                          <NoteActionDialog
                            actionPath={`${reviewPath}/reject`}
                            title={`Reject ${label}`}
                            description="Tell the club what needs to change."
                            triggerLabel="Reject"
                            isNoteRequired
                            variant="destructive"
                            size="xs"
                          />
                        )}
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </Card>
  );
}
