import { request, requestJson } from "@/lib/api"

// The backend's /canvas routes, as `modules/canvas/schemas.py` returns them.

export type ConnectionStatus = {
  connected: boolean
  base_url: string | null
  user_name: string | null
  // The background to-do refresh: its switch, when it last worked, and the code
  // of how its last pass failed.
  auto_refresh: boolean
  refreshed_at: string | null
  refresh_error: string | null
}

export type ConnectionInput = { base_url: string; token: string }

export type SyncedCourse = {
  canvas_id: number
  name: string
  workspace_id: number
  // Files edited in Canvas whose kept copy was replaced.
  refreshed: string[]
  // Kept files Canvas no longer lists; they stay.
  gone: string[]
}

export type StaleCourse = {
  canvas_id: number
  name: string
  workspace_id: number
  changed: string[]
  gone: string[]
}

export function readConnection(
  signal?: AbortSignal
): Promise<ConnectionStatus> {
  return requestJson<ConnectionStatus>("/canvas/connection", { signal })
}

export function connectCanvas(
  input: ConnectionInput
): Promise<ConnectionStatus> {
  return requestJson<ConnectionStatus>("/canvas/connection", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  })
}

/** Turns the background to-do refresh on or off. */
export function setAutoRefresh(enabled: boolean): Promise<ConnectionStatus> {
  return requestJson<ConnectionStatus>("/canvas/connection", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ auto_refresh: enabled }),
  })
}

export async function disconnectCanvas(): Promise<void> {
  await request("/canvas/connection", { method: "DELETE" })
}

/** Reads Canvas and brings the workspaces in line; it can take minutes. */
export async function syncCanvas(): Promise<SyncedCourse[]> {
  const result = await requestJson<{ courses: SyncedCourse[] }>(
    "/canvas/sync",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    }
  )
  return result.courses
}

// The last Sync or Check, as `modules/canvas/runlog` serves it: coded lines the
// app words itself.
export type LogEntry = {
  n: number
  level: "info" | "error"
  code: string
  params: Record<string, string | number | boolean>
}

export type RunLog = {
  run: number
  kind: "sync" | "check" | null
  state: "idle" | "running" | "done" | "failed"
  entries: LogEntry[]
  next: number
}

/** The lines after `after` of run `run`, or the whole current log when `run` is
 * not the current run. */
export function readLog(
  run: number | null,
  after: number,
  signal?: AbortSignal
): Promise<RunLog> {
  const query = new URLSearchParams({ after: String(after) })
  if (run !== null) query.set("run", String(run))
  return requestJson<RunLog>(`/canvas/log?${query}`, { signal })
}

/** Which kept files no longer match Canvas; asks, and changes nothing. */
export async function checkCanvas(): Promise<StaleCourse[]> {
  const result = await requestJson<{ courses: StaleCourse[] }>("/canvas/stale")
  return result.courses
}
