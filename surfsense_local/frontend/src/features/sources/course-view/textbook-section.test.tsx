import { cleanup, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import type { WorkspaceDocument } from "../api"
import { TextbookSection } from "./textbook-section"

const api = vi.hoisted(() => ({ uploadDocuments: vi.fn() }))
vi.mock("../api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api")>()),
  uploadDocuments: api.uploadDocuments,
}))

function book(id: number, title: string): WorkspaceDocument {
  return {
    id,
    title,
    document_type: "FILE",
    mime_type: "application/pdf",
    status: "ready",
    error_message: null,
    created_at: "2026-11-27T00:00:00Z",
    updated_at: "2026-11-27T00:00:00Z",
    folder_id: 9,
  }
}

function show(documents: WorkspaceDocument[] = []) {
  const handlers = {
    onSelectionChange: vi.fn(),
    onPreview: vi.fn(),
    onImported: vi.fn(),
  }
  const view = render(
    <TextbookSection
      workspaceId={2}
      folderId={9}
      documents={documents}
      selectedDocumentIds={[]}
      {...handlers}
    />
  )
  return { ...handlers, view }
}

function fileInput(container: HTMLElement) {
  return container.querySelector<HTMLInputElement>('input[type="file"]')!
}

beforeEach(() => {
  api.uploadDocuments
    .mockReset()
    .mockResolvedValue({ created: [], duplicates: [], rejected: [] })
})

afterEach(cleanup)

describe("Textbook section", () => {
  it("says so when no book is imported", () => {
    show()

    expect(screen.getByText("No textbook yet.")).toBeTruthy()
  })

  it("lists each book with a tick box and previews it by name", async () => {
    const { onSelectionChange, onPreview } = show([book(5, "Networks.pdf")])

    await userEvent.click(
      screen.getByRole("checkbox", { name: "Select Networks.pdf" })
    )
    await userEvent.click(screen.getByRole("button", { name: "Networks.pdf" }))

    expect(onSelectionChange).toHaveBeenCalledWith(5, true)
    expect(onPreview).toHaveBeenCalledWith(5)
  })

  it("accepts only the book formats", () => {
    const { view } = show()

    expect(fileInput(view.container).getAttribute("accept")).toBe(
      ".pdf,.epub,.mobi,.azw3"
    )
  })

  it("files the imported book in the Textbook folder and refreshes", async () => {
    const { view, onImported } = show()
    const file = new File(["x"], "Networks.pdf", { type: "application/pdf" })

    await userEvent.upload(fileInput(view.container), file)

    expect(api.uploadDocuments).toHaveBeenCalledWith(2, [file], undefined, {
      folderId: 9,
    })
    expect(onImported).toHaveBeenCalled()
  })

  it("shows an error when the upload fails and keeps the button usable", async () => {
    api.uploadDocuments.mockRejectedValue(new Error("down"))
    const { view, onImported } = show()

    await userEvent.upload(
      fileInput(view.container),
      new File(["x"], "Networks.pdf", { type: "application/pdf" })
    )

    expect(await screen.findByRole("alert")).toBeTruthy()
    expect(onImported).not.toHaveBeenCalled()
    expect(
      (
        screen.getByRole("button", {
          name: "Import textbook",
        }) as HTMLButtonElement
      ).disabled
    ).toBe(false)
  })

  it("shows an error when the server rejects the book", async () => {
    api.uploadDocuments.mockResolvedValue({
      created: [],
      duplicates: [],
      rejected: [{ filename: "Networks.pdf", reason: "unsupported" }],
    })
    const { view } = show()

    await userEvent.upload(
      fileInput(view.container),
      new File(["x"], "Networks.pdf", { type: "application/pdf" })
    )

    expect(await screen.findByRole("alert")).toBeTruthy()
  })
})
