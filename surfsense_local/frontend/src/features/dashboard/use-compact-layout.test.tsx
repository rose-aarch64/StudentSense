import { afterEach, describe, expect, it, vi } from "vitest"
import { act, cleanup, screen } from "@testing-library/react"

import { render } from "@/test-utils"

import { useCompactLayout } from "./use-compact-layout"

function Probe() {
  return <p>{useCompactLayout() ? "compact" : "desktop"}</p>
}

/** A matchMedia whose answer the test sets, and whose listeners it can fire. */
function stubMedia(matches: boolean) {
  const listeners = new Set<() => void>()
  const state = { matches }
  const matchMedia = vi.fn((query: string) => ({
    media: query,
    get matches() {
      return state.matches
    },
    addEventListener: (_type: string, listener: () => void) =>
      listeners.add(listener),
    removeEventListener: (_type: string, listener: () => void) =>
      listeners.delete(listener),
  }))
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: matchMedia,
  })
  return {
    matchMedia,
    listeners,
    set(next: boolean) {
      state.matches = next
      for (const listener of [...listeners]) listener()
    },
  }
}

afterEach(() => {
  cleanup()
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: undefined,
  })
})

describe("the compact layout hook", () => {
  it("is false where matchMedia does not exist", () => {
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      value: undefined,
    })

    render(<Probe />)

    expect(screen.getByText("desktop")).toBeTruthy()
  })

  it("asks for widths below 1024 px", () => {
    const media = stubMedia(false)

    render(<Probe />)

    expect(media.matchMedia).toHaveBeenCalledWith("(max-width: 1023px)")
  })

  it("follows the query as the window crosses the breakpoint", () => {
    const media = stubMedia(false)
    render(<Probe />)
    expect(screen.getByText("desktop")).toBeTruthy()

    act(() => media.set(true))
    expect(screen.getByText("compact")).toBeTruthy()

    act(() => media.set(false))
    expect(screen.getByText("desktop")).toBeTruthy()
  })

  it("stops listening when unmounted", () => {
    const media = stubMedia(true)
    const { unmount } = render(<Probe />)
    expect(media.listeners.size).toBe(1)

    unmount()

    expect(media.listeners.size).toBe(0)
  })
})
