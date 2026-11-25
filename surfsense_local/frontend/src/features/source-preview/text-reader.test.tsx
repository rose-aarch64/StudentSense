import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, screen } from "@testing-library/react"

import { render } from "@/test-utils"

import { canPreview } from "./can-preview"
import { SourcePreviewPanel } from "./source-preview-panel"

const MARKDOWN_FILE = {
  id: 7,
  title: "syllabus.md",
  document_type: "FILE" as const,
  mime_type: "text/markdown",
  status: "ready" as const,
  error_message: null,
  created_at: "2026-10-04T00:00:00Z",
  updated_at: "2026-10-04T00:00:00Z",
  folder_id: 1,
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe("canPreview", () => {
  it("accepts every source that has finished reading", () => {
    expect(canPreview(MARKDOWN_FILE)).toBe(true)
    expect(canPreview({ ...MARKDOWN_FILE, mime_type: null })).toBe(true)
    expect(canPreview({ ...MARKDOWN_FILE, document_type: "NOTE" })).toBe(true)
  })

  it("refuses a source with no text yet", () => {
    expect(canPreview({ ...MARKDOWN_FILE, status: "pending" })).toBe(false)
    expect(canPreview({ ...MARKDOWN_FILE, status: "failed" })).toBe(false)
  })
})

describe("the source preview of a source with no file viewer", () => {
  it("reads a markdown file as formatted text without an edit step", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              ...MARKDOWN_FILE,
              content: "# Week one\n\nRead chapter **two**.",
            }),
            { status: 200, headers: { "content-type": "application/json" } }
          )
      )
    )

    render(
      <SourcePreviewPanel
        workspaceId={1}
        document={MARKDOWN_FILE}
        onOpen={vi.fn()}
        onClose={vi.fn()}
      />
    )

    expect(
      await screen.findByRole("heading", { name: "Week one" })
    ).toBeTruthy()
    expect(screen.getByText("two")).toBeTruthy()
    expect(screen.queryByRole("textbox")).toBeNull()
  })

  it("says so when the source has no text", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ ...MARKDOWN_FILE, content: null }), {
            status: 200,
            headers: { "content-type": "application/json" },
          })
      )
    )

    render(
      <SourcePreviewPanel
        workspaceId={1}
        document={MARKDOWN_FILE}
        onOpen={vi.fn()}
        onClose={vi.fn()}
      />
    )

    expect(
      await screen.findByText("This source has no text to show")
    ).toBeTruthy()
  })
})
