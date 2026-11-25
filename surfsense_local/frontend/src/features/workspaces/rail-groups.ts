import type { Workspace, WorkspaceFolder } from "./api"

export type RailGroup = { folder: WorkspaceFolder; workspaces: Workspace[] }

/**
 * The rail's order: unfiled workspaces as given, then each folder, empty ones
 * too, with its workspaces. A workspace naming a folder this list lacks is
 * unfiled, so a stale id never hides it.
 */
export function groupWorkspaces(
  workspaces: Workspace[],
  folders: WorkspaceFolder[]
): { unfiled: Workspace[]; groups: RailGroup[] } {
  const known = new Set(folders.map((folder) => folder.id))
  return {
    unfiled: workspaces.filter(
      (workspace) =>
        workspace.folder_id == null || !known.has(workspace.folder_id)
    ),
    groups: folders.map((folder) => ({
      folder,
      workspaces: workspaces.filter(
        (workspace) => workspace.folder_id === folder.id
      ),
    })),
  }
}
