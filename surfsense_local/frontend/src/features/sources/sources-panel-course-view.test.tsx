import { cleanup, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

import { TooltipProvider } from "@/components/ui/tooltip"

import type { WorkspaceDocument } from "./api"
import { SourcesPanel } from "./sources-panel"

const DOCUMENT: WorkspaceDocument = {
  id: 7,
  title: "guide.txt",
  document_type: "FILE",
  mime_type: "text/plain",
  status: "ready",
  error_message: null,
  created_at: "2026-09-05T00:00:00Z",
  updated_at: "2026-09-05T00:00:00Z",
}

function show(courseView?: ReactNode) {
  render(
    <TooltipProvider>
      <SourcesPanel
        documents={[DOCUMENT]}
        selectedDocumentIds={[]}
        highlightedDocumentId={null}
        isLoading={false}
        isDeleting={false}
        error={null}
        onOpen={vi.fn()}
        onReveal={vi.fn()}
        onRetry={vi.fn()}
        onCancel={vi.fn()}
        onDelete={vi.fn()}
        onDeleteSelected={vi.fn()}
        onSelectionChange={vi.fn()}
        onToggleAll={vi.fn()}
        courseView={courseView}
      />
    </TooltipProvider>
  )
}

afterEach(cleanup)

describe("Sources panel with a course view", () => {
  it("offers no switch for a workspace with no course view", () => {
    show()

    expect(screen.queryByRole("button", { name: "Canvas" })).toBeNull()
    expect(screen.getByText("guide.txt")).toBeTruthy()
  })

  it("starts on the files and swaps to the modules and back", async () => {
    show(<p>the modules pane</p>)
    expect(screen.getByText("guide.txt")).toBeTruthy()
    expect(screen.queryByText("the modules pane")).toBeNull()

    await userEvent.click(screen.getByRole("button", { name: "Canvas" }))

    expect(screen.getByText("the modules pane")).toBeTruthy()
    expect(screen.queryByText("guide.txt")).toBeNull()

    await userEvent.click(screen.getByRole("button", { name: "Files" }))

    expect(screen.getByText("guide.txt")).toBeTruthy()
    expect(screen.queryByText("the modules pane")).toBeNull()
  })
})
