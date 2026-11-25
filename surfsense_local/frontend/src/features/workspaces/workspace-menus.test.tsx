import { afterEach, describe, expect, it, vi } from "vitest"
import { act, cleanup, fireEvent, screen } from "@testing-library/react"
import userEvent, { type UserEvent } from "@testing-library/user-event"

import { render } from "@/test-utils"

import type { Workspace, WorkspaceFolder } from "./api"
import { WorkspaceRail } from "./workspace-rail"

const STAMP = "2026-11-24T00:00:00Z"
const PHOTO: Workspace = {
  id: 2,
  name: "Photography",
  icon: null,
  folder_id: null,
  created_at: STAMP,
  updated_at: STAMP,
}
const FALL: WorkspaceFolder = {
  id: 10,
  name: "2026/FA",
  created_at: STAMP,
  updated_at: STAMP,
}

function renderRail() {
  const handlers = {
    onSetIcon: vi.fn(async () => true),
    onMoveToFolder: vi.fn(async () => true),
    onCreateFolder: vi.fn(async (name: string) => ({
      ...FALL,
      id: 11,
      name,
    })),
    onRenameFolder: vi.fn(async () => true),
    onDeleteFolder: vi.fn(async () => true),
  }
  render(
    <WorkspaceRail
      workspaces={[{ ...PHOTO, id: 1, name: "Personal" }, PHOTO]}
      folders={[FALL]}
      activeWorkspaceId={1}
      isMutating={false}
      onSelect={vi.fn()}
      onCreate={vi.fn(async () => true)}
      onRename={vi.fn(async () => true)}
      onDelete={vi.fn(async () => true)}
      onOpenSettings={vi.fn()}
      {...handlers}
    />
  )
  return handlers
}

afterEach(cleanup)

/**
 * Opens "Move to folder" by keyboard and clicks an item. The pointer is left
 * out: its hover intent closes a submenu the moment it crosses to an item.
 */
async function chooseFromMoveMenu(
  user: UserEvent,
  name: string,
  taken: () => void
) {
  const trigger = await screen.findByRole("menuitem", {
    name: "Move to folder",
  })
  act(() => trigger.focus())
  await user.keyboard("{ArrowRight}")
  fireEvent.click(await screen.findByRole("menuitem", { name }))
  await vi.waitFor(taken)
}

describe("a workspace's menu", () => {
  it("picks an icon in a dialog and saves its key", async () => {
    const handlers = renderRail()
    // A submenu's popup is `pointer-events: none` until it has finished opening.
    const user = userEvent.setup({ pointerEventsCheck: 0 })

    fireEvent.contextMenu(screen.getByRole("button", { name: "Photography" }))
    await user.click(await screen.findByRole("menuitem", { name: "Icon…" }))
    await user.click(await screen.findByRole("button", { name: "camera" }))
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(handlers.onSetIcon).toHaveBeenCalledWith(2, "camera")
  })

  it("goes back to initials with None", async () => {
    const handlers = renderRail()
    // A submenu's popup is `pointer-events: none` until it has finished opening.
    const user = userEvent.setup({ pointerEventsCheck: 0 })

    fireEvent.contextMenu(screen.getByRole("button", { name: "Photography" }))
    await user.click(await screen.findByRole("menuitem", { name: "Icon…" }))
    await user.click(await screen.findByRole("button", { name: "None" }))

    expect(handlers.onSetIcon).toHaveBeenCalledWith(2, null)
  })

  it("moves into a folder and out again", async () => {
    const handlers = renderRail()
    // A submenu's popup is `pointer-events: none` until it has finished opening.
    const user = userEvent.setup({ pointerEventsCheck: 0 })

    fireEvent.contextMenu(screen.getByRole("button", { name: "Photography" }))
    await chooseFromMoveMenu(user, "2026/FA", () =>
      expect(handlers.onMoveToFolder).toHaveBeenCalledWith(2, 10)
    )

    fireEvent.contextMenu(screen.getByRole("button", { name: "Photography" }))
    await chooseFromMoveMenu(user, "No folder", () =>
      expect(handlers.onMoveToFolder).toHaveBeenLastCalledWith(2, null)
    )
  })

  it("makes a new folder from the menu and moves the workspace into it", async () => {
    const handlers = renderRail()
    // A submenu's popup is `pointer-events: none` until it has finished opening.
    const user = userEvent.setup({ pointerEventsCheck: 0 })

    fireEvent.contextMenu(screen.getByRole("button", { name: "Photography" }))
    await chooseFromMoveMenu(user, "New folder…", () =>
      expect(screen.getByRole("textbox")).toBeTruthy()
    )
    await user.type(await screen.findByRole("textbox"), "Spring")
    await user.click(screen.getByRole("button", { name: "Create" }))

    expect(handlers.onCreateFolder).toHaveBeenCalledWith("Spring")
    await vi.waitFor(() =>
      expect(handlers.onMoveToFolder).toHaveBeenCalledWith(2, 11)
    )
  })
})

describe("a folder's menu", () => {
  it("renames the folder", async () => {
    const handlers = renderRail()
    // A submenu's popup is `pointer-events: none` until it has finished opening.
    const user = userEvent.setup({ pointerEventsCheck: 0 })

    fireEvent.contextMenu(screen.getByRole("button", { name: /2026\/FA/ }))
    await user.click(await screen.findByRole("menuitem", { name: "Rename" }))
    const box = await screen.findByRole("textbox", { name: "Folder name" })
    await user.clear(box)
    await user.type(box, "Fall 2026")
    await user.click(screen.getByRole("button", { name: "Rename" }))

    expect(handlers.onRenameFolder).toHaveBeenCalledWith(10, "Fall 2026")
  })

  it("deletes the folder after a confirmation that says its workspaces stay", async () => {
    const handlers = renderRail()
    // A submenu's popup is `pointer-events: none` until it has finished opening.
    const user = userEvent.setup({ pointerEventsCheck: 0 })

    fireEvent.contextMenu(screen.getByRole("button", { name: /2026\/FA/ }))
    await user.click(await screen.findByRole("menuitem", { name: "Delete" }))

    expect(await screen.findByText(/workspaces are kept/i)).toBeTruthy()
    expect(handlers.onDeleteFolder).not.toHaveBeenCalled()
    await user.click(screen.getByRole("button", { name: "Delete folder" }))

    expect(handlers.onDeleteFolder).toHaveBeenCalledWith(10)
  })
})
