import { useMutation, useQueryClient } from "@tanstack/react-query";

export function useClubMutation<TVariables = void>(
  mutationFn: (variables: TVariables) => Promise<unknown>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["clubs"] }),
  });
}
