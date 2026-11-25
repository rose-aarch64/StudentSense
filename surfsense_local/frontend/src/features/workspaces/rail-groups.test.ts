import { describe, expect, it } from "vitest"

import type { Workspace, WorkspaceFolder } from "./api"
import { groupWorkspaces } from "./rail-groups"

function workspace(id: number, folder_id: number | null = null): Workspace {
  return {
    id,
    name: `W${id}`,
    icon: null,
    folder_id,
    created_at: "2026-11-24T00:00:00Z",
    updated_at: "2026-11-24T00:00:00Z",
  }
}

function folder(id: number): WorkspaceFolder {
  return {
    id,
    name: `F${id}`,
    created_at: "2026-11-24T00:00:00Z",
    updated_at: "2026-11-24T00:00:00Z",
  }
}

describe("groupWorkspaces", () => {
  it("keeps unfiled workspaces in order and puts filed ones under their folder", () => {
    const grouped = groupWorkspaces(
      [workspace(1), workspace(2, 10), workspace(3), workspace(4, 10)],
      [folder(10)]
    )

    expect(grouped.unfiled.map((w) => w.id)).toEqual([1, 3])
    expect(
      grouped.groups.map((g) => [g.folder.id, g.workspaces.map((w) => w.id)])
    ).toEqual([[10, [2, 4]]])
  })

  it("keeps a folder with no workspaces, so it can still be renamed or deleted", () => {
    const grouped = groupWorkspaces([workspace(1)], [folder(10), folder(11)])

    expect(grouped.groups.map((g) => g.folder.id)).toEqual([10, 11])
    expect(grouped.groups[1].workspaces).toEqual([])
  })

  it("treats a workspace whose folder is unknown as unfiled", () => {
    const grouped = groupWorkspaces([workspace(1, 99)], [folder(10)])

    expect(grouped.unfiled.map((w) => w.id)).toEqual([1])
  })
})
