import { Badge } from "@/components/ui/badge";
import { REQUEST_STATUS_BADGES } from "@/lib/request-labels";
import type { RequestStatus } from "@/lib/request-types";

export function RequestStatusBadge({ status }: { status: RequestStatus }) {
  const { label, color } = REQUEST_STATUS_BADGES[status];
  return (
    <Badge variant="light" size="sm" color={color}>
      {label}
    </Badge>
  );
}
