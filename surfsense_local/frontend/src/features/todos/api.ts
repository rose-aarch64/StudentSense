import { requestJson, requestVoid } from "@/lib/api"

// The backend's /todos routes, as `modules/todos/schemas.py` returns them.

export type TodoSource = "manual" | "canvas"

export type Todo = {
  id: number
  workspace_id: number | null
  title: string
  due_at: string | null
  done_at: string | null
  done: boolean
  source: TodoSource
  source_key: string | null
  created_at: string
  updated_at: string
}

export type NewTodo = { title: string; due_at?: string }

export function createTodo(
  input: NewTodo,
  signal?: AbortSignal
): Promise<Todo> {
  return requestJson<Todo>("/todos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
    signal,
  })
}

export type TodoChange = { done: boolean }

export function updateTodo(
  id: number,
  change: TodoChange,
  signal?: AbortSignal
): Promise<Todo> {
  return requestJson<Todo>(`/todos/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(change),
    signal,
  })
}

export function deleteTodo(id: number, signal?: AbortSignal): Promise<void> {
  return requestVoid(`/todos/${id}`, { method: "DELETE", signal })
}

/** Open tasks first, soonest due first: the order the list shows. */
export function listTodos(signal?: AbortSignal): Promise<Todo[]> {
  return requestJson<Todo[]>("/todos", { signal })
}

export type BoardDay = { date: string; today: boolean; todos: Todo[] }

/** The list in its sections, as `modules/todos/board/schemas.py` returns it. */
export type Board = {
  today: string
  overdue: Todo[]
  this_week: BoardDay[]
  next_week: Todo[]
  in_two_weeks: Todo[]
  future: Todo[]
  undated: Todo[]
  done: Todo[]
  // Late by over a week or finished over a month ago: set aside, not deleted.
  older: Todo[]
}

export function readBoard(signal?: AbortSignal): Promise<Board> {
  return requestJson<Board>("/todos/board", { signal })
}
