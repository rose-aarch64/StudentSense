import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { render } from "@/test-utils"

import { CompactSheet } from "./compact-sheet"

function sheet(open: boolean, onClose = vi.fn()) {
  render(
    <CompactSheet
      open={open}
      side="start"
      label="Menu"
      closeLabel="Close menu"
      onClose={onClose}
    >
      <p>inside</p>
    </CompactSheet>
  )
  return onClose
}

afterEach(cleanup)

describe("a compact sheet", () => {
  it("keeps its children mounted but out of the accessibility tree while closed", () => {
    sheet(false)

    expect(screen.getByText("inside")).toBeTruthy()
    expect(screen.queryByRole("dialog")).toBeNull()
    expect(
      screen.getByText("inside").closest('[aria-hidden="true"]')
    ).not.toBeNull()
  })

  it("is a named dialog with a close button when open", () => {
    sheet(true)

    expect(screen.getByRole("dialog", { name: "Menu" })).toBeTruthy()
    expect(screen.getByRole("button", { name: "Close menu" })).toBeTruthy()
  })

  it("closes from its button and from Escape", async () => {
    const onClose = sheet(true)
    const user = userEvent.setup()

    await user.click(screen.getByRole("button", { name: "Close menu" }))
    expect(onClose).toHaveBeenCalledTimes(1)

    await user.keyboard("{Escape}")
    expect(onClose).toHaveBeenCalledTimes(2)
  })

  it("does not close on Escape while closed", async () => {
    const onClose = sheet(false)

    await userEvent.setup().keyboard("{Escape}")

    expect(onClose).not.toHaveBeenCalled()
  })
})
