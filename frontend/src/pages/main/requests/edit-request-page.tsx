import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { OctagonAlertIcon } from "@/icons";
import { apiFetch } from "@/lib/api";
import type { RequestDetail, RequestInput } from "@/lib/request-types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router";
import { RequestForm } from "./request-form";
import { toFormValues } from "./request-schema";

export default function EditRequestPage() {
  const { requestId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const requestPath = `/requests/${requestId}`;

  const request = useQuery({
    queryKey: ["requests", requestId],
    queryFn: () => apiFetch<RequestDetail>(requestPath),
  });

  const updateRequest = useMutation({
    mutationFn: (input: RequestInput) =>
      apiFetch<RequestDetail>(requestPath, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    meta: { successMessage: "Request updated" },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["requests"] });
      void navigate(requestPath);
    },
  });

  if (request.error) {
    return (
      <Alert variant="destructive" className="p-4">
        <OctagonAlertIcon className="size-5" />
        <AlertTitle>Could not load request</AlertTitle>
        <AlertDescription>{request.error.message}</AlertDescription>
      </Alert>
    );
  }

  if (!request.data) {
    return (
      <Skeleton
        role="status"
        aria-label="Loading request"
        className="h-64 max-w-2xl bg-gray-200 dark:bg-gray-800"
      />
    );
  }

  return (
    <div>
      <PageMeta title="Edit request" description="Change a request" />
      <PageBreadcrumb pageTitle="Edit request" />

      <RequestForm
        defaultValues={toFormValues(request.data)}
        isTypeLocked
        submitLabel="Save changes"
        isPending={updateRequest.isPending}
        error={updateRequest.error}
        cancelPath={requestPath}
        onSubmit={(input) => updateRequest.mutate(input)}
      />
    </div>
  );
}
