import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { readPersona, writePersona } from "./api"

const personaQueryKey = ["persona"] as const

export function usePersona() {
  return useQuery({
    queryKey: personaQueryKey,
    queryFn: ({ signal }) => readPersona(signal),
  })
}

export function useSavePersona() {
  const client = useQueryClient()
  return useMutation({
    // Wrapped: Query's second argument is its context, not an AbortSignal.
    mutationFn: (text: string) => writePersona(text),
    onSuccess: (saved) => client.setQueryData(personaQueryKey, saved),
  })
}
