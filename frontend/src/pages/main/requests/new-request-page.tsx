import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { apiFetch } from "@/lib/api";
import type { RequestDetail, RequestInput } from "@/lib/request-types";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router";
import { RequestForm } from "./request-form";
import { EMPTY_REQUEST_FORM } from "./request-schema";

export default function NewRequestPage() {
  const { clubId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const createRequest = useMutation({
    mutationFn: (input: RequestInput) =>
      apiFetch<RequestDetail>(`/clubs/${clubId}/requests`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    meta: { successMessage: "Request saved as a draft" },
    onSuccess: (request) => {
      void queryClient.invalidateQueries({ queryKey: ["requests"] });
      void navigate(`/requests/${request.id}`);
    },
  });

  return (
    <div>
      <PageMeta
        title="New request"
        description="Ask for funding or a room booking"
      />
      <PageBreadcrumb pageTitle="New request" />

      <RequestForm
        defaultValues={EMPTY_REQUEST_FORM}
        isTypeLocked={false}
        submitLabel="Save draft"
        isPending={createRequest.isPending}
        error={createRequest.error}
        cancelPath={`/clubs/${clubId}?tab=requests`}
        onSubmit={(input) => createRequest.mutate(input)}
      />
    </div>
  );
}
