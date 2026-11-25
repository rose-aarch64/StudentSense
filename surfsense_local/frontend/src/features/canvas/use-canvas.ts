import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { todosQueryKey } from "@/features/todos/use-todos"

import {
  checkCanvas,
  connectCanvas,
  disconnectCanvas,
  readConnection,
  setAutoRefresh,
  syncCanvas,
  type ConnectionInput,
  type ConnectionStatus,
} from "./api"

export const canvasConnectionKey = ["canvas", "connection"] as const

const DISCONNECTED: ConnectionStatus = {
  connected: false,
  base_url: null,
  user_name: null,
  auto_refresh: false,
  refreshed_at: null,
  refresh_error: null,
}

export function useConnection() {
  return useQuery({
    queryKey: canvasConnectionKey,
    queryFn: ({ signal }) => readConnection(signal),
  })
}

// Every mutation function is wrapped: Query passes its own context as a second
// argument, which a bare API function would take for its AbortSignal.

export function useConnect() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (input: ConnectionInput) => connectCanvas(input),
    onSuccess: (status) => client.setQueryData(canvasConnectionKey, status),
  })
}

export function useSetAutoRefresh() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (enabled: boolean) => setAutoRefresh(enabled),
    onSuccess: (status) => client.setQueryData(canvasConnectionKey, status),
  })
}

export function useDisconnect() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => disconnectCanvas(),
    onSuccess: () => client.setQueryData(canvasConnectionKey, DISCONNECTED),
  })
}

export function useSync() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => syncCanvas(),
    // A sync adds tasks for assignments.
    onSuccess: () => client.invalidateQueries({ queryKey: todosQueryKey }),
  })
}

export function useCheck() {
  return useMutation({ mutationFn: () => checkCanvas() })
}
