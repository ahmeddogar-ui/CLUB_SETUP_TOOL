import { useMutation, useQueryClient } from "@tanstack/react-query";

/** A change to a club: refetches every club query and confirms with a toast. */
export function useClubMutation<TVariables = void>(
  mutationFn: (variables: TVariables) => Promise<unknown>,
  successMessage: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    meta: { successMessage },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["clubs"] }),
  });
}
