import { cleanup, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"

import type { WorkspaceDocument } from "../api"
import type { CourseView } from "./course-api"
import { CoursePane } from "./course-pane"

// The note's own text is the reader's business; here only which note is shown.
vi.mock("@/features/source-preview/text-reader", () => ({
  TextReader: ({ document }: { document: WorkspaceDocument }) => (
    <p>note text {document.id}</p>
  ),
}))

const VIEW: CourseView = {
  synced: true,
  needs_sync: false,
  textbook_folder_id: 9,
  notes: { syllabus: 21, assignments: 22, links: 23 },
  files: {},
  modules: [
    {
      id: 1,
      name: "Module A",
      folder_id: 5,
      items: [
        {
          type: "Page",
          title: "Intro",
          document_id: 11,
          url: null,
          due_at: null,
          points: null,
        },
      ],
    },
  ],
}

function document(
  id: number,
  title: string,
  folder: number
): WorkspaceDocument {
  return {
    id,
    title,
    document_type: "FILE",
    mime_type: "application/pdf",
    status: "ready",
    error_message: null,
    created_at: "2026-11-27T00:00:00Z",
    updated_at: "2026-11-27T00:00:00Z",
    folder_id: folder,
  }
}

function show() {
  const onPreview = vi.fn()
  render(
    <CoursePane
      view={VIEW}
      workspaceId={2}
      documents={[
        document(11, "Intro", 5),
        document(31, "Networks.pdf", 9),
        document(21, "Canvas · Syllabus", 3),
        document(22, "Canvas · Assignments", 3),
        document(23, "Canvas · Links", 3),
      ]}
      selectedDocumentIds={[]}
      folderTicks={new Map()}
      onSelectionChange={vi.fn()}
      onFolderSelectionChange={vi.fn()}
      onPreview={onPreview}
      onImported={vi.fn()}
    />
  )
  return { onPreview }
}

afterEach(cleanup)

describe("course pane", () => {
  it("opens on the modules", () => {
    show()

    expect(screen.getByRole("heading", { name: "Module A" })).toBeTruthy()
    expect(screen.queryByRole("button", { name: "Import textbook" })).toBeNull()
  })

  it("shows a summary note in place from its chip, as a tab, and offers only the notes that exist", async () => {
    const { onPreview } = show()

    await userEvent.click(screen.getByRole("button", { name: "Syllabus" }))

    expect(screen.getByText("note text 21")).toBeTruthy()
    expect(screen.queryByRole("heading", { name: "Module A" })).toBeNull()
    expect(
      screen
        .getByRole("button", { name: "Syllabus" })
        .getAttribute("aria-pressed")
    ).toBe("true")
    expect(onPreview).not.toHaveBeenCalled()
    expect(screen.queryByRole("button", { name: "Announcements" })).toBeNull()
  })

  it("moves between the note tabs and shows the chosen one", async () => {
    show()
    await userEvent.click(screen.getByRole("button", { name: "Syllabus" }))

    await userEvent.click(screen.getByRole("button", { name: "Assignments" }))

    expect(screen.getByText("note text 22")).toBeTruthy()
    expect(screen.queryByText("note text 21")).toBeNull()
  })

  it("shows the Textbook with only the books in its folder", async () => {
    show()

    await userEvent.click(screen.getByRole("button", { name: "Textbook" }))

    expect(screen.getByRole("button", { name: "Import textbook" })).toBeTruthy()
    expect(screen.getByRole("button", { name: "Networks.pdf" })).toBeTruthy()
    expect(screen.queryByRole("button", { name: "Intro" })).toBeNull()
  })

  it("returns to the modules from the Modules chip", async () => {
    show()
    await userEvent.click(screen.getByRole("button", { name: "Textbook" }))

    await userEvent.click(screen.getByRole("button", { name: "Modules" }))

    expect(screen.getByRole("heading", { name: "Module A" })).toBeTruthy()
  })
})
