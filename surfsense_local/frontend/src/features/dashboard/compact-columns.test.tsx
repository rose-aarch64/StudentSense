import type { ComponentProps } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { render } from "@/test-utils"

import { CompactColumns } from "./compact-columns"

function columns(over: Partial<ComponentProps<typeof CompactColumns>> = {}) {
  const props = {
    chat: <p>chat</p>,
    rail: <nav aria-label="Workspaces">rail</nav>,
    sidebar: <p>sidebar</p>,
    sources: <p>sources list</p>,
    selectedSourceCount: 2,
    drawerOpen: false,
    onDrawerClose: vi.fn(),
    detail: <p>detail</p>,
    detailOpen: false,
    onDetailClose: vi.fn(),
    ...over,
  }
  render(<CompactColumns {...props} />)
  return props
}

afterEach(cleanup)

/** On screen: mounted and not inside a `hidden` ancestor. */
function shown(text: string) {
  return screen.getByText(text).closest("[hidden]") === null
}

describe("the compact columns", () => {
  it("shows the chat and keeps both sheets out of the accessibility tree until opened", () => {
    columns()

    expect(screen.getByText("chat")).toBeTruthy()
    expect(screen.queryByRole("dialog")).toBeNull()
  })

  it("opens the drawer with the rail above the sidebar", () => {
    columns({ drawerOpen: true })

    const drawer = screen.getByRole("dialog", { name: "Menu" })
    const rail = within(drawer).getByText("rail")
    const sidebar = within(drawer).getByText("sidebar")
    expect(
      rail.compareDocumentPosition(sidebar) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy()
  })

  it("keeps the sources in a collapsed bar below the chat, with the count of ticked ones", () => {
    columns({ selectedSourceCount: 2 })

    const bar = screen.getByRole("button", { name: "Sources (2 selected)" })
    expect(bar.getAttribute("aria-expanded")).toBe("false")
    expect(shown("chat")).toBe(true)
    expect(shown("sources list")).toBe(false)
    expect(
      screen.getByText("chat").compareDocumentPosition(bar) &
        Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy()
  })

  it("opens the list over the chat and brings the chat back when the bar is tapped again", async () => {
    columns()
    const user = userEvent.setup()
    const bar = screen.getByRole("button", { name: "Sources (2 selected)" })

    await user.click(bar)

    expect(bar.getAttribute("aria-expanded")).toBe("true")
    expect(shown("sources list")).toBe(true)
    expect(shown("chat")).toBe(false)

    await user.click(bar)

    expect(shown("chat")).toBe(true)
    expect(shown("sources list")).toBe(false)
  })

  it("keeps the chat and the list mounted, so a draft, a scroll and a filter survive", async () => {
    columns()
    const chat = screen.getByText("chat")
    const list = screen.getByText("sources list")
    const user = userEvent.setup()
    const bar = screen.getByRole("button", { name: "Sources (2 selected)" })

    await user.click(bar)
    await user.click(bar)

    expect(screen.getByText("chat")).toBe(chat)
    expect(screen.getByText("sources list")).toBe(list)
  })

  it("closes the drawer from its button and from Escape", async () => {
    const { onDrawerClose } = columns({ drawerOpen: true })
    const user = userEvent.setup()

    await user.click(screen.getByRole("button", { name: "Close menu" }))
    await user.keyboard("{Escape}")

    expect(onDrawerClose).toHaveBeenCalledTimes(2)
  })

  it("opens the detail sheet over the chat and goes back", async () => {
    const { onDetailClose } = columns({ detailOpen: true })

    const detail = screen.getByRole("dialog", { name: "Details" })
    expect(within(detail).getByText("detail")).toBeTruthy()

    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Back to the chat" }))

    expect(onDetailClose).toHaveBeenCalledTimes(1)
  })
})
