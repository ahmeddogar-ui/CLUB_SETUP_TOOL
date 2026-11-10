import { Badge } from "@/components/ui/badge";
import { CLUB_STATUS_BADGES, REQUIREMENT_STATUS_BADGES } from "@/lib/labels";
import type { ClubStatus, RequirementStatus } from "@/lib/types";

export function ClubStatusBadge({ status }: { status: ClubStatus }) {
  const { label, color } = CLUB_STATUS_BADGES[status];
  return (
    <Badge variant="light" size="sm" color={color}>
      {label}
    </Badge>
  );
}

export function RequirementStatusBadge({
  status,
}: {
  status: RequirementStatus;
}) {
  const { label, color } = REQUIREMENT_STATUS_BADGES[status];
  return (
    <Badge variant="light" size="sm" color={color}>
      {label}
    </Badge>
  );
}
