import { Card, CardTitle } from "@/components/ui/card";
import { formatDateTime, USER_ROLE_LABELS } from "@/lib/labels";
import type { RequestDetail } from "@/lib/request-types";

type ApprovalsCardProps = Pick<
  RequestDetail,
  "approval_steps" | "approvals" | "awaiting_role"
>;

/** The approval steps in order: who approved each, which one is awaited and
 * which haven't begun. Steps are matched to approvals by role. */
export function ApprovalsCard({
  approval_steps,
  approvals,
  awaiting_role,
}: ApprovalsCardProps) {
  return (
    <Card className="w-full rounded-2xl border border-gray-200 bg-white p-5 sm:p-6 dark:border-gray-800 dark:bg-white/3">
      <CardTitle className="text-lg font-semibold text-gray-800 dark:text-white/90">
        Approvals
      </CardTitle>

      <ol aria-label="Approval steps" className="space-y-4">
        {approval_steps.map((role, index) => {
          const approval = approvals.find(
            (candidate) => candidate.role === role,
          );
          return (
            <li key={index} className="text-sm">
              <p className="font-medium text-gray-800 dark:text-white/90">
                {index + 1}. {USER_ROLE_LABELS[role]}
              </p>
              {approval ? (
                <div className="mt-1 text-gray-600 dark:text-gray-400">
                  <p>
                    Approved by {approval.approver_name} ·{" "}
                    {formatDateTime(approval.approved_at)}
                  </p>
                  {approval.note && (
                    <p className="mt-1 whitespace-pre-line">{approval.note}</p>
                  )}
                </div>
              ) : (
                <p className="mt-1 text-gray-500 dark:text-gray-400">
                  {role === awaiting_role ? "Waiting" : "Not started"}
                </p>
              )}
            </li>
          );
        })}
      </ol>
    </Card>
  );
}
