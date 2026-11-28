import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"

import { CitationChunkText } from "@/features/chat/citation-chunk-text"

import { CanvasFileLinksProvider } from "./canvas-file-links"

const HELD =
  "[the policy](https://school.edu/courses/91884/files/1827589?wrap=1)"
const NOT_HELD = "[the sheet](https://school.edu/courses/91884/files/42)"
const OUTSIDE = "[a site](https://example.org/page)"

// Streamdown's own link, with its safety check, is a button with no address.
const STREAMDOWN_LINK = '[data-streamdown="link"]'

function show(content: string, withProvider = true) {
  const onOpen = vi.fn()
  const text = <CitationChunkText content={content} />
  const view = render(
    withProvider ? (
      <CanvasFileLinksProvider files={{ "1827589": 31 }} onOpen={onOpen}>
        {text}
      </CanvasFileLinksProvider>
    ) : (
      text
    )
  )
  return { onOpen, container: view.container }
}

afterEach(cleanup)

describe("a note's links to Canvas files", () => {
  it("opens the file the class holds, in place of the link's own address", async () => {
    const { onOpen, container } = show(HELD)

    await userEvent.click(screen.getByText("the policy"))

    expect(onOpen).toHaveBeenCalledWith(31)
    expect(container.querySelector(STREAMDOWN_LINK)).toBeNull()
  })

  it("leaves a modified click to the browser, as ctrl or cmd opens a new tab", () => {
    const { onOpen } = show(HELD)

    fireEvent.click(screen.getByText("the policy"), { ctrlKey: true })
    fireEvent.click(screen.getByText("the policy"), { metaKey: true })

    expect(onOpen).not.toHaveBeenCalled()
  })

  it("leaves a link whose file is not held to Streamdown's own link", async () => {
    const { onOpen, container } = show(NOT_HELD)

    await userEvent.click(screen.getByText("the sheet"))

    expect(onOpen).not.toHaveBeenCalled()
    expect(container.querySelector(STREAMDOWN_LINK)).not.toBeNull()
  })

  it("leaves a link to an outside site to Streamdown's own link", async () => {
    const { onOpen, container } = show(OUTSIDE)

    await userEvent.click(screen.getByText("a site"))

    expect(onOpen).not.toHaveBeenCalled()
    expect(container.querySelector(STREAMDOWN_LINK)).not.toBeNull()
  })

  it("shows Streamdown's own link for every link with no provider", () => {
    const { container } = show(HELD, false)

    expect(container.querySelector(STREAMDOWN_LINK)).not.toBeNull()
  })
})
