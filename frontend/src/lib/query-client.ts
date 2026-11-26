import { ApiError } from "@/lib/api";
import { MutationCache, QueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

declare module "@tanstack/react-query" {
  interface Register {
    /** A mutation that sets `successMessage` confirms itself with a toast. */
    mutationMeta: { successMessage?: string };
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
      onSuccess: (_data, _variables, _context, mutation) => {
        const message = mutation.meta?.successMessage;
        if (message) toast.success(message);
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
