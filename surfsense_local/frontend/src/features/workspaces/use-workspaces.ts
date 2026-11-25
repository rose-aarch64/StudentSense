import { useMemo, useState } from "react"

import { intl } from "@/i18n/intl"

import {
  createWorkspace,
  createWorkspaceFolder,
  deleteWorkspace,
  deleteWorkspaceFolder,
  listWorkspaceFolders,
  listWorkspaces,
  renameWorkspace,
  renameWorkspaceFolder,
  updateWorkspace,
  type Workspace,
  type WorkspaceChange,
  type WorkspaceFolder,
} from "./api"
import { readStoredWorkspaceId, rememberWorkspace } from "./last-workspace"

function readLastWorkspaceId(workspaces: Workspace[]): number | null {
  const stored = readStoredWorkspaceId()
  if (workspaces.some((workspace) => workspace.id === stored)) {
    return stored
  }
  // Null when the list is empty, so nothing is active.
  return workspaces[0]?.id ?? null
}

function messageFrom(error: unknown) {
  return error instanceof Error
    ? error.message
    : intl.formatMessage({
        id: "workspaces_unexpected_error",
        defaultMessage: "An unexpected error occurred",
      })
}

export function useWorkspaces(
  initialWorkspaces: Workspace[],
  initialFolders: WorkspaceFolder[] = []
) {
  const [workspaces, setWorkspaces] = useState(initialWorkspaces)
  const [folders, setFolders] = useState(initialFolders)
  const [activeId, setActiveId] = useState(() =>
    readLastWorkspaceId(initialWorkspaces)
  )
  const [error, setError] = useState<string | null>(null)
  const [isMutating, setIsMutating] = useState(false)

  const activeWorkspace = useMemo(
    () => workspaces.find((workspace) => workspace.id === activeId),
    [activeId, workspaces]
  )

  const select = (id: number) => {
    if (
      id === activeId ||
      !workspaces.some((workspace) => workspace.id === id)
    ) {
      return
    }
    rememberWorkspace(id)
    setActiveId(id)
  }

  const create = async (name: string) => {
    setIsMutating(true)
    setError(null)
    try {
      const workspace = await createWorkspace(name)
      setWorkspaces((current) => [...current, workspace])
      rememberWorkspace(workspace.id)
      setActiveId(workspace.id)
      return true
    } catch (cause) {
      setError(messageFrom(cause))
      return false
    } finally {
      setIsMutating(false)
    }
  }

  const rename = async (id: number, name: string) => {
    setIsMutating(true)
    setError(null)
    try {
      const workspace = await renameWorkspace(id, name)
      setWorkspaces((current) =>
        current.map((candidate) =>
          candidate.id === workspace.id ? workspace : candidate
        )
      )
      return true
    } catch (cause) {
      setError(messageFrom(cause))
      return false
    } finally {
      setIsMutating(false)
    }
  }

  const remove = async (id: number) => {
    setIsMutating(true)
    setError(null)
    try {
      await deleteWorkspace(id)
      const remaining = workspaces.filter((workspace) => workspace.id !== id)
      setWorkspaces(remaining)

      // Deleting the last one leaves nothing active; the empty state takes over.
      if (id === activeId) {
        const nextId = remaining[0]?.id ?? null
        if (nextId !== null) rememberWorkspace(nextId)
        setActiveId(nextId)
      }
      return true
    } catch (cause) {
      setError(messageFrom(cause))
      return false
    } finally {
      setIsMutating(false)
    }
  }

  // Runs one change, keeping its error and busy state like the rest; false on failure.
  const attempt = async <T>(
    run: () => Promise<T>,
    apply: (result: T) => void
  ) => {
    setIsMutating(true)
    setError(null)
    try {
      apply(await run())
      return true
    } catch (cause) {
      setError(messageFrom(cause))
      return false
    } finally {
      setIsMutating(false)
    }
  }

  const change = (id: number, fields: WorkspaceChange) =>
    attempt(
      () => updateWorkspace(id, fields),
      (workspace) =>
        setWorkspaces((current) =>
          current.map((candidate) =>
            candidate.id === workspace.id ? workspace : candidate
          )
        )
    )

  const setIcon = (id: number, icon: string | null) => change(id, { icon })

  const moveToFolder = (id: number, folderId: number | null) =>
    change(id, { folder_id: folderId })

  const createFolder = async (name: string) => {
    let created: WorkspaceFolder | null = null
    await attempt(
      () => createWorkspaceFolder(name),
      (folder) => {
        created = folder
        setFolders((current) => [...current, folder])
      }
    )
    return created
  }

  const renameFolder = (id: number, name: string) =>
    attempt(
      () => renameWorkspaceFolder(id, name),
      (folder) =>
        setFolders((current) =>
          current.map((candidate) =>
            candidate.id === folder.id ? folder : candidate
          )
        )
    )

  // The server unfiles the folder's workspaces; the list follows without a reload.
  const removeFolder = (id: number) =>
    attempt(
      () => deleteWorkspaceFolder(id),
      () => {
        setFolders((current) => current.filter((folder) => folder.id !== id))
        setWorkspaces((current) =>
          current.map((workspace) =>
            workspace.folder_id === id
              ? { ...workspace, folder_id: null }
              : workspace
          )
        )
      }
    )

  // After a change made outside this hook (an import); lands on `focusId`.
  const reload = async (focusId: number) => {
    const [next, nextFolders] = await Promise.all([
      listWorkspaces(),
      listWorkspaceFolders().catch(() => null),
    ])
    setWorkspaces(next)
    if (nextFolders !== null) setFolders(nextFolders)
    if (next.some((workspace) => workspace.id === focusId)) {
      rememberWorkspace(focusId)
      setActiveId(focusId)
    }
  }

  return {
    workspaces,
    folders,
    activeWorkspace,
    error,
    isMutating,
    select,
    create,
    rename,
    remove,
    setIcon,
    moveToFolder,
    createFolder,
    renameFolder,
    removeFolder,
    reload,
    clearError: () => setError(null),
  }
}
