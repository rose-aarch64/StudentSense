import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, screen } from "@testing-library/react"

import { render } from "@/test-utils"

import { DashboardShell } from "./dashboard-shell"

/** A matchMedia that answers true only for the compact query, or never. */
function stubMedia(compact: boolean) {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: vi.fn((query: string) => ({
      media: query,
      matches: compact && query === "(max-width: 1023px)",
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  })
}

afterEach(() => {
  cleanup()
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: undefined,
  })
})

describe("the dashboard shell", () => {
  it("keeps the desktop grid and its minimum width when not compact", () => {
    stubMedia(false)

    render(<DashboardShell />)

    const shell = screen.getByRole("main")
    expect(shell.className).toContain("min-w-[calc(73rem+160px)]")
    expect(shell.className).toContain("grid-cols-[216px_minmax(0,1fr)]")
  })

  it("is one column with no minimum width when compact", () => {
    stubMedia(true)

    render(<DashboardShell />)

    const shell = screen.getByRole("main")
    expect(shell.className).toContain("grid-cols-1")
    expect(shell.className).toContain("min-w-0")
    expect(shell.className).not.toContain("min-w-[calc(73rem+160px)]")
    expect(shell.className).not.toContain("216px")
  })
})
