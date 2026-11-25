import type { ComponentProps } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { render } from "@/test-utils"

import type { Workspace, WorkspaceFolder } from "./api"
import { WorkspaceRail } from "./workspace-rail"

const STAMP = "2026-11-24T00:00:00Z"

function workspace(
  id: number,
  name: string,
  extra: Partial<Workspace> = {}
): Workspace {
  return {
    id,
    name,
    icon: null,
    folder_id: null,
    created_at: STAMP,
    updated_at: STAMP,
    ...extra,
  }
}

const FALL: WorkspaceFolder = {
  id: 10,
  name: "2026/FA",
  created_at: STAMP,
  updated_at: STAMP,
}

function renderRail(
  workspaces: Workspace[],
  folders: WorkspaceFolder[],
  onSelect = vi.fn(),
  overrides: Partial<ComponentProps<typeof WorkspaceRail>> = {}
) {
  render(
    <WorkspaceRail
      workspaces={workspaces}
      folders={folders}
      activeWorkspaceId={workspaces[0].id}
      isMutating={false}
      onSelect={onSelect}
      onCreate={vi.fn(async () => true)}
      onRename={vi.fn(async () => true)}
      onDelete={vi.fn(async () => true)}
      onOpenSettings={vi.fn()}
      onSetIcon={vi.fn(async () => true)}
      onMoveToFolder={vi.fn(async () => true)}
      onCreateFolder={vi.fn(async () => null)}
      onRenameFolder={vi.fn(async () => true)}
      onDeleteFolder={vi.fn(async () => true)}
      {...overrides}
    />
  )
  return onSelect
}

afterEach(() => {
  cleanup()
  localStorage.clear()
})

describe("the workspace rail", () => {
  it("lists workspaces as rows with their names", () => {
    renderRail([workspace(1, "Personal"), workspace(2, "Photography")], [])

    expect(screen.getByRole("button", { name: "Personal" })).toBeTruthy()
    expect(screen.getByText("Photography")).toBeTruthy()
  })

  it("shows initials for a workspace with no icon, and none behind an icon", () => {
    renderRail(
      [
        workspace(1, "Network Security", { icon: "shield" }),
        workspace(2, "Photography"),
      ],
      []
    )

    expect(screen.queryByText("NS")).toBeNull()
    expect(screen.getByText("P")).toBeTruthy()
  })

  it("shows initials for an icon key this release does not know", () => {
    renderRail([workspace(1, "Photography", { icon: "future-icon" })], [])

    expect(screen.getByText("P")).toBeTruthy()
  })

  it("marks the selected row and selects on click", async () => {
    const onSelect = renderRail(
      [workspace(1, "Personal"), workspace(2, "Photography")],
      []
    )
    const user = userEvent.setup()

    expect(
      screen
        .getByRole("button", { name: "Personal" })
        .getAttribute("aria-current")
    ).toBe("page")
    await user.click(screen.getByRole("button", { name: "Photography" }))

    expect(onSelect).toHaveBeenCalledWith(2)
  })

  it("puts a folder's workspaces under its header and hides them when it is closed", async () => {
    renderRail(
      [
        workspace(1, "Personal"),
        workspace(2, "Photography", { folder_id: 10 }),
      ],
      [FALL]
    )
    const user = userEvent.setup()

    expect(screen.getByText("Photography")).toBeTruthy()
    await user.click(screen.getByRole("button", { name: /2026\/FA/ }))

    expect(screen.queryByText("Photography")).toBeNull()
    expect(
      screen
        .getByRole("button", { name: /2026\/FA/ })
        .getAttribute("aria-expanded")
    ).toBe("false")
  })

  it("remembers a closed folder after the rail is rebuilt", async () => {
    const rows = [
      workspace(1, "Personal"),
      workspace(2, "Photography", { folder_id: 10 }),
    ]
    renderRail(rows, [FALL])
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: /2026\/FA/ }))
    cleanup()

    renderRail(rows, [FALL])

    expect(screen.queryByText("Photography")).toBeNull()
  })

  it("keeps a folder with no workspaces, so it can still be managed", () => {
    renderRail([workspace(1, "Personal")], [FALL])

    expect(
      within(screen.getByRole("navigation")).getByRole("button", {
        name: /2026\/FA/,
      })
    ).toBeTruthy()
  })

  it("ignores a remembered closed folder that no longer exists", () => {
    localStorage.setItem("surfsense:collapsed-folders:v1", "[99]")

    renderRail(
      [
        workspace(1, "Personal"),
        workspace(2, "Photography", { folder_id: 10 }),
      ],
      [FALL]
    )

    expect(screen.getByText("Photography")).toBeTruthy()
  })

  it("opens a menu with Workspace and Folder from the New row", async () => {
    renderRail([workspace(1, "Personal")], [])

    await userEvent.setup().click(screen.getByRole("button", { name: "New" }))

    expect(
      await screen.findByRole("menuitem", { name: "Workspace" })
    ).toBeTruthy()
    expect(screen.getByRole("menuitem", { name: "Folder" })).toBeTruthy()
  })

  it("makes a workspace from the New menu", async () => {
    const onCreate = vi.fn(async () => true)
    renderRail([workspace(1, "Personal")], [], vi.fn(), { onCreate })
    const user = userEvent.setup()

    await user.click(screen.getByRole("button", { name: "New" }))
    await user.click(await screen.findByRole("menuitem", { name: "Workspace" }))
    await user.type(await screen.findByLabelText("Workspace name"), "Bio")
    await user.click(screen.getByRole("button", { name: "Create" }))

    await waitFor(() => expect(onCreate).toHaveBeenCalledWith("Bio"))
  })

  it("makes an empty folder from the New menu", async () => {
    const onCreateFolder = vi.fn(async () => FALL)
    const onMoveToFolder = vi.fn(async () => true)
    renderRail([workspace(1, "Personal")], [], vi.fn(), {
      onCreateFolder,
      onMoveToFolder,
    })
    const user = userEvent.setup()

    await user.click(screen.getByRole("button", { name: "New" }))
    await user.click(await screen.findByRole("menuitem", { name: "Folder" }))
    await user.type(await screen.findByLabelText("Folder name"), "2026/FA")
    await user.click(screen.getByRole("button", { name: "Create" }))

    await waitFor(() => expect(onCreateFolder).toHaveBeenCalledWith("2026/FA"))
    expect(onMoveToFolder).not.toHaveBeenCalled()
  })
})
