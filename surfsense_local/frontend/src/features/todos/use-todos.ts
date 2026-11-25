import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import {
  createTodo,
  deleteTodo,
  readBoard,
  updateTodo,
  type NewTodo,
  type TodoChange,
} from "./api"

export const todosQueryKey = ["todos"] as const

/** The list in its sections. Under the tasks' key, so any change refetches it. */
export function useBoard() {
  return useQuery({
    queryKey: [...todosQueryKey, "board"],
    queryFn: ({ signal }) => readBoard(signal),
  })
}

/** The list is the server's, in its own order, so a change refetches it. */
export function useAddTodo() {
  const client = useQueryClient()
  return useMutation({
    // Wrapped: a mutation function's second argument is Query's context, which
    // a bare createTodo would take for its AbortSignal.
    mutationFn: (todo: NewTodo) => createTodo(todo),
    onSuccess: () => client.invalidateQueries({ queryKey: todosQueryKey }),
  })
}

export function useDeleteTodo() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => deleteTodo(id),
    onSuccess: () => client.invalidateQueries({ queryKey: todosQueryKey }),
  })
}

export function useChangeTodo() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ id, change }: { id: number; change: TodoChange }) =>
      updateTodo(id, change),
    onSuccess: () => client.invalidateQueries({ queryKey: todosQueryKey }),
  })
}
