import { ApiError } from "@/lib/api";
import { MutationCache, QueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

declare module "@tanstack/react-query" {
  interface Register {
    /** A mutation that sets `successMessage` confirms itself with a toast; a
     * function builds the message from the variables the mutation ran with. */
    mutationMeta: { successMessage?: string | ((variables: never) => string) };
  }
}

const MAX_RETRIES = 3;

const isClientError = (error: Error) =>
  error instanceof ApiError && error.status < 500;

/** The app's one QueryClient setup, shared by main.tsx and the tests. Every
 * mutation's confirmation toast is raised here, so no component repeats it. */
export function createQueryClient({ retry = true } = {}) {
  return new QueryClient({
    mutationCache: new MutationCache({
      onSuccess: (_data, variables, _context, mutation) => {
        const message = mutation.meta?.successMessage;
        if (!message) return;
        // The mutation that set the function typed its own variables.
        const text =
          typeof message === "function"
            ? (message as (variables: unknown) => string)(variables)
            : message;
        toast.success(text);
      },
    }),
    defaultOptions: {
      queries: {
        retry: (failureCount, error) =>
          retry && !isClientError(error) && failureCount < MAX_RETRIES,
      },
    },
  });
}
