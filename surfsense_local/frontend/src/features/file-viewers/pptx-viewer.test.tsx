import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { PptxViewer } from "./pptx-viewer"

const renderer = vi.hoisted(() => ({ open: vi.fn(), destroy: vi.fn() }))
vi.mock("@aiden0z/pptx-renderer", () => ({
  RECOMMENDED_ZIP_LIMITS: {},
  PptxViewer: { open: renderer.open },
}))

const props = {
  url: "/api/workspaces/2/documents/12/original",
  mimeType:
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  sizeBytes: null,
  title: "Slides",
  actionsContainer: null,
}

beforeEach(() => {
  renderer.open.mockReset().mockResolvedValue({ destroy: renderer.destroy })
  renderer.destroy.mockReset()
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe("source slide viewer", () => {
  it("draws the slides of the file at its url", async () => {
    const fetchMock = vi.fn<typeof fetch>(
      async () => new Response(new ArrayBuffer(4))
    )
    vi.stubGlobal("fetch", fetchMock)

    render(<PptxViewer {...props} />)

    await vi.waitFor(() => expect(renderer.open).toHaveBeenCalled())
    expect(fetchMock.mock.calls[0]![0]).toBe(props.url)
    expect(renderer.open.mock.lastCall![0].byteLength).toBe(4)
  })

  it("says so when the server refuses the file", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("no", { status: 500 }))
    )

    render(<PptxViewer {...props} />)

    expect(await screen.findByText(/Server returned 500/)).toBeTruthy()
    expect(renderer.open).not.toHaveBeenCalled()
  })

  it("lets go of the renderer when closed", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(new ArrayBuffer(4)))
    )

    const view = render(<PptxViewer {...props} />)
    await vi.waitFor(() => expect(renderer.open).toHaveBeenCalled())
    view.unmount()

    await vi.waitFor(() => expect(renderer.destroy).toHaveBeenCalled())
  })
})
