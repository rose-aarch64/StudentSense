import { cleanup, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"

import { ViewSwitch } from "./view-switch"

afterEach(cleanup)

describe("Files and Modules switch", () => {
  it("marks the chosen view and reports a change", async () => {
    const onChange = vi.fn()
    render(<ViewSwitch value="files" onChange={onChange} />)

    expect(
      screen.getByRole("button", { name: "Files" }).getAttribute("aria-pressed")
    ).toBe("true")
    expect(
      screen
        .getByRole("button", { name: "Canvas" })
        .getAttribute("aria-pressed")
    ).toBe("false")

    await userEvent.click(screen.getByRole("button", { name: "Canvas" }))

    expect(onChange).toHaveBeenCalledWith("modules")
  })
})
