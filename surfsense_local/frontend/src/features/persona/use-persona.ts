import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import {
  readAgentPersona,
  readPersona,
  writeAgentPersona,
  writePersona,
} from "./api"

const personaQueryKey = ["persona"] as const
const agentPersonaQueryKey = ["persona", "agent"] as const

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

export function useAgentPersona() {
  return useQuery({
    queryKey: agentPersonaQueryKey,
    queryFn: ({ signal }) => readAgentPersona(signal),
  })
}

export function useSaveAgentPersona() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (text: string) => writeAgentPersona(text),
    onSuccess: (saved) => client.setQueryData(agentPersonaQueryKey, saved),
  })
}
