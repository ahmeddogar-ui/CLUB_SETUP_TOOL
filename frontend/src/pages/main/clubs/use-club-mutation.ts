import {
  type QueryKey,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";

/** A change to a club, or to another resource via `queryKey` (request
 * actions pass ["requests"]): refetches every query under the key and
 * confirms with a toast. */
export function useClubMutation<TVariables = void>(
  mutationFn: (variables: TVariables) => Promise<unknown>,
  successMessage: string,
  queryKey: QueryKey = ["clubs"],
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    meta: { successMessage },
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });
}
