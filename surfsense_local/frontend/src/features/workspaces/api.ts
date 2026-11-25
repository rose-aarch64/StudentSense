import { request, requestJson, requestVoid } from "@/lib/api"

import { parseWorkspaceEvents, type WorkspaceEvent } from "./read-sse"

export type Workspace = {
  id: number
  name: string
  // A key into the interface's icon set; null shows the initials. Both are
  // absent from an API without folders.
  icon?: string | null
  folder_id?: number | null
  created_at: string
  updated_at: string
}

export type WorkspaceFolder = {
  id: number
  name: string
  created_at: string
  updated_at: string
}

/** The fields a change names; an unnamed one is left alone, null clears. */
export type WorkspaceChange = {
  name?: string
  icon?: string | null
  folder_id?: number | null
}

export function updateWorkspace(
  id: number,
  change: WorkspaceChange,
  signal?: AbortSignal
): Promise<Workspace> {
  return requestJson<Workspace>(`/workspaces/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(change),
    signal,
  })
}

export function listWorkspaceFolders(
  signal?: AbortSignal
): Promise<WorkspaceFolder[]> {
  return requestJson<WorkspaceFolder[]>("/workspace-folders", { signal })
}

export function createWorkspaceFolder(
  name: string,
  signal?: AbortSignal
): Promise<WorkspaceFolder> {
  return requestJson<WorkspaceFolder>("/workspace-folders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
    signal,
  })
}

export function renameWorkspaceFolder(
  id: number,
  name: string,
  signal?: AbortSignal
): Promise<WorkspaceFolder> {
  return requestJson<WorkspaceFolder>(`/workspace-folders/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
    signal,
  })
}

export function deleteWorkspaceFolder(
  id: number,
  signal?: AbortSignal
): Promise<void> {
  return requestVoid(`/workspace-folders/${id}`, { method: "DELETE", signal })
}

export function listWorkspaces(signal?: AbortSignal): Promise<Workspace[]> {
  return requestJson<Workspace[]>("/workspaces", { signal })
}

export function createWorkspace(
  name: string,
  signal?: AbortSignal
): Promise<Workspace> {
  return requestJson<Workspace>("/workspaces", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
    signal,
  })
}

export function renameWorkspace(
  id: number,
  name: string,
  signal?: AbortSignal
): Promise<Workspace> {
  return requestJson<Workspace>(`/workspaces/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
    signal,
  })
}

export function deleteWorkspace(
  id: number,
  signal?: AbortSignal
): Promise<void> {
  return requestVoid(`/workspaces/${id}`, { method: "DELETE", signal })
}

/**
 * `connected` once the API is listening for this client, then one event per
 * change, until the stream ends or `signal` aborts. An event says that rows
 * changed, never what they became: the caller reloads.
 */
export async function* followWorkspaceEvents(
  workspaceId: number,
  signal: AbortSignal
): AsyncGenerator<WorkspaceEvent> {
  const response = await request(`/workspaces/${workspaceId}/events`, {
    signal,
  })
  if (!response.body) return
  yield* parseWorkspaceEvents(response.body)
}
