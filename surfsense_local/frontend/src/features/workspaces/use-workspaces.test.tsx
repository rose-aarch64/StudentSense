import { afterEach, describe, expect, it, vi } from "vitest"
import { act, cleanup, renderHook } from "@testing-library/react"

import type { Workspace, WorkspaceFolder } from "./api"
import { useWorkspaces } from "./use-workspaces"

const STAMP = "2026-11-24T00:00:00Z"

function workspace(id: number, folder_id: number | null = null): Workspace {
  return {
    id,
    name: `W${id}`,
    icon: null,
    folder_id,
    created_at: STAMP,
    updated_at: STAMP,
  }
}

const FOLDER: WorkspaceFolder = {
  id: 10,
  name: "2026/FA",
  created_at: STAMP,
  updated_at: STAMP,
}

/** The workspace and folder routes; every request is recorded. */
function stubApi(serverWorkspaces: Workspace[]) {
  const calls: Array<{ path: string; method: string; body: unknown }> = []
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input)
      const method = (init?.method ?? "GET").toUpperCase()
      const body = init?.body ? JSON.parse(String(init.body)) : undefined
      calls.push({ path, method, body })
      const one = path.match(/^\/workspaces\/(\d+)$/)
      if (one && method === "PATCH") {
        const found = serverWorkspaces.find((w) => w.id === Number(one[1]))
        return Response.json({ ...found, ...body })
      }
      if (path === "/workspace-folders" && method === "POST") {
        return Response.json(
          { ...FOLDER, id: 11, name: body.name },
          { status: 201 }
        )
      }
      if (path.startsWith("/workspace-folders/") && method === "DELETE") {
        return new Response(null, { status: 204 })
      }
      return Response.json([])
    })
  )
  return calls
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe("useWorkspaces folders and icons", () => {
  it("files a workspace and sends only the folder", async () => {
    const calls = stubApi([workspace(1)])
    const { result } = renderHook(() => useWorkspaces([workspace(1)], [FOLDER]))

    await act(() => result.current.moveToFolder(1, 10))

    expect(result.current.workspaces[0].folder_id).toBe(10)
    expect(calls.at(-1)?.body).toEqual({ folder_id: 10 })
  })

  it("sets and clears an icon", async () => {
    const calls = stubApi([workspace(1)])
    const { result } = renderHook(() => useWorkspaces([workspace(1)], []))

    await act(() => result.current.setIcon(1, "camera"))
    expect(result.current.workspaces[0].icon).toBe("camera")
    await act(() => result.current.setIcon(1, null))

    expect(result.current.workspaces[0].icon).toBeNull()
    expect(calls.at(-1)?.body).toEqual({ icon: null })
  })

  it("adds a created folder and returns it", async () => {
    stubApi([])
    const { result } = renderHook(() => useWorkspaces([], []))

    let created: WorkspaceFolder | null = null
    await act(async () => {
      created = await result.current.createFolder("2026/SP")
    })

    expect(created).toMatchObject({ id: 11, name: "2026/SP" })
    expect(result.current.folders.map((f) => f.id)).toEqual([11])
  })

  it("unfiles a deleted folder's workspaces and keeps them", async () => {
    stubApi([])
    const { result } = renderHook(() =>
      useWorkspaces([workspace(1, 10), workspace(2)], [FOLDER])
    )

    await act(() => result.current.removeFolder(10))

    expect(result.current.folders).toEqual([])
    expect(result.current.workspaces.map((w) => [w.id, w.folder_id])).toEqual([
      [1, null],
      [2, null],
    ])
  })
})
