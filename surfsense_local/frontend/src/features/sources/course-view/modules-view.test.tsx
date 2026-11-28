import { cleanup, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"

import type { CourseView, ItemView } from "./course-api"
import { ModulesView } from "./modules-view"

function item(overrides: Partial<ItemView> & { title: string }): ItemView {
  return {
    type: "Page",
    document_id: null,
    url: null,
    due_at: null,
    points: null,
    ...overrides,
  }
}

const VIEW: CourseView = {
  synced: true,
  needs_sync: false,
  textbook_folder_id: 9,
  notes: {},
  files: {},
  modules: [
    {
      id: 1,
      name: "Module A Intro",
      folder_id: 5,
      items: [
        item({ type: "SubHeader", title: "LEARN" }),
        item({ title: "Learning Objectives", document_id: 11 }),
        item({ type: "File", title: "Slides A1", document_id: 12 }),
        item({ type: "SubHeader", title: "APPLY" }),
        item({
          type: "Assignment",
          title: "Lab A2",
          document_id: 13,
          due_at: "2026-09-08T04:00:00Z",
          points: 100,
        }),
        item({
          type: "ExternalUrl",
          title: "Blog",
          url: "https://example.org/blog",
        }),
        item({ type: "Quiz", title: "Hidden quiz" }),
      ],
    },
    {
      id: 2,
      name: "Policy",
      folder_id: null,
      items: [item({ type: "SubHeader", title: "No Device" })],
    },
  ],
}

function show(overrides: Partial<Parameters<typeof ModulesView>[0]> = {}) {
  const handlers = {
    onSelectionChange: vi.fn(),
    onFolderSelectionChange: vi.fn(),
    onPreview: vi.fn(),
  }
  render(
    <ModulesView
      view={VIEW}
      readyDocumentIds={new Set([11, 12, 13])}
      selectedDocumentIds={[11]}
      folderTicks={new Map([[5, "mixed"]])}
      {...handlers}
      {...overrides}
    />
  )
  return handlers
}

afterEach(cleanup)

describe("Modules view", () => {
  it("renders items in the stored order", () => {
    show()

    const rows = screen.getAllByRole("listitem").map((li) => li.textContent)

    const titles = [
      "LEARN",
      "Learning Objectives",
      "Slides A1",
      "APPLY",
      "Lab A2",
      "Blog",
      "Hidden quiz",
    ]
    const at = titles.map((title) =>
      rows.findIndex((row) => row?.includes(title))
    )
    expect(at.every((index) => index >= 0)).toBe(true)
    expect([...at].sort((a, b) => a - b)).toEqual(at)
  })

  it("shows a module header half-filled when some of its folder is ticked", () => {
    show()

    const header = screen.getByRole("checkbox", {
      name: "Select module Module A Intro",
    })

    expect(header.getAttribute("aria-checked")).toBe("mixed")
  })

  it("ticks a row through the same selection a source row uses", async () => {
    const { onSelectionChange } = show()

    await userEvent.click(
      screen.getByRole("checkbox", { name: "Select Slides A1" })
    )

    expect(onSelectionChange).toHaveBeenCalledWith(12, true)
  })

  it("ticks a whole module through its folder", async () => {
    const { onFolderSelectionChange } = show()

    await userEvent.click(
      screen.getByRole("checkbox", { name: "Select module Module A Intro" })
    )

    expect(onFolderSelectionChange).toHaveBeenCalledWith(5, true)
  })

  it("shows a module half-filled when an item filed in another module is unticked", async () => {
    const shared: CourseView = {
      ...VIEW,
      modules: [
        {
          id: 3,
          name: "Module B",
          folder_id: 6,
          items: [
            item({ title: "Own page", document_id: 21 }),
            item({ title: "Lab A2", type: "Assignment", document_id: 13 }),
          ],
        },
      ],
    }
    const { onFolderSelectionChange, onSelectionChange } = show({
      view: shared,
      readyDocumentIds: new Set([13, 21]),
      selectedDocumentIds: [21],
      folderTicks: new Map([[6, "checked"]]),
    })
    const header = screen.getByRole("checkbox", {
      name: "Select module Module B",
    })

    expect(header.getAttribute("aria-checked")).toBe("mixed")

    await userEvent.click(header)

    expect(onFolderSelectionChange).toHaveBeenCalledWith(6, true)
    expect(onSelectionChange).toHaveBeenCalledWith(13, true)
  })

  it("gives a module with no folder no header checkbox", () => {
    show()

    expect(screen.getByText("Policy")).toBeTruthy()
    expect(
      screen.queryByRole("checkbox", { name: "Select module Policy" })
    ).toBeNull()
  })

  it("opens a link's address in a new tab and gives it no checkbox", () => {
    show()

    const link = screen.getByRole("link", { name: /Blog/ })

    expect(link.getAttribute("href")).toBe("https://example.org/blog")
    expect(link.getAttribute("target")).toBe("_blank")
    expect(screen.queryByRole("checkbox", { name: "Select Blog" })).toBeNull()
  })

  it("shows an item with no source and no address as plain text", () => {
    show()

    expect(screen.getByText("Hidden quiz")).toBeTruthy()
    expect(
      screen.queryByRole("checkbox", { name: "Select Hidden quiz" })
    ).toBeNull()
    expect(screen.queryByRole("link", { name: /Hidden quiz/ })).toBeNull()
  })

  it("shows a lab's due date and points", () => {
    show()

    expect(screen.getByText(/100/)).toBeTruthy()
    expect(screen.getByText(/Sep 8/)).toBeTruthy()
  })
})
