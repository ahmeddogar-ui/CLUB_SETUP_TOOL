import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/contexts";
import { OctagonAlertIcon } from "@/icons";
import { apiFetch } from "@/lib/api";
import { EDITABLE_STATUSES } from "@/lib/labels";
import type { Club, ClubEvent, Requirement } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router";
import { ClubActions } from "./club-actions";
import { EditClubDialog } from "./edit-club-dialog";
import { HistoryCard } from "./history-card";
import { RequirementsCard } from "./requirements-card";
import { ClubStatusBadge } from "./status-badge";

export default function ClubDetailPage() {
  const { clubId } = useParams();
  const { user } = useAuth();

  const club = useQuery({
    queryKey: ["clubs", clubId],
    queryFn: () => apiFetch<Club>(`/clubs/${clubId}`),
  });
  const requirements = useQuery({
    queryKey: ["clubs", clubId, "requirements"],
    queryFn: () => apiFetch<Requirement[]>(`/clubs/${clubId}/requirements`),
  });
  const events = useQuery({
    queryKey: ["clubs", clubId, "events"],
    queryFn: () => apiFetch<ClubEvent[]>(`/clubs/${clubId}/events`),
  });

  const error = club.error ?? requirements.error ?? events.error;
  if (error) {
    return (
      <Alert variant="destructive" className="p-4">
        <OctagonAlertIcon className="size-5" />
        <AlertTitle>Could not load club</AlertTitle>
        <AlertDescription>{error.message}</AlertDescription>
      </Alert>
    );
  }

  if (!club.data || !requirements.data || !events.data) {
    return (
      <div className="flex justify-center py-12">
        <Spinner className="size-6 text-brand-500" />
      </div>
    );
  }

  const isAdmin = user?.role === "admin";
  const isOwner = club.data.submitter_id === user?.id;
  const isEditable = isOwner && EDITABLE_STATUSES.includes(club.data.status);

  return (
    <div>
      <PageMeta
        title={`${club.data.name} | Club Setup`}
        description={club.data.description}
      />
      <PageBreadcrumb pageTitle={club.data.name} />

      <div className="space-y-6">
        <Card className="rounded-2xl border border-gray-200 bg-white p-5 sm:p-6 dark:border-gray-800 dark:bg-white/3">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-2">
              <ClubStatusBadge status={club.data.status} />
              <p className="text-sm whitespace-pre-line text-gray-700 dark:text-gray-400">
                {club.data.description}
              </p>
            </div>
            {isEditable && <EditClubDialog club={club.data} />}
          </div>

          <ClubActions
            club={club.data}
            canSubmit={isEditable}
            isAdmin={isAdmin}
          />
        </Card>

        <RequirementsCard
          requirements={requirements.data}
          canEditLinks={isEditable}
          canReview={isAdmin && club.data.status === "under_review"}
        />

        <HistoryCard events={events.data} requirements={requirements.data} />
      </div>
    </div>
  );
}
