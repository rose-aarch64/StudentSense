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
