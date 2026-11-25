import { afterEach, describe, expect, it } from "vitest"
import { act, cleanup } from "@testing-library/react"

import { render } from "@/test-utils"

import { useAppHeight } from "./use-app-height"

function Probe({ active }: { active: boolean }) {
  useAppHeight(active)
  return null
}

const read = () =>
  document.documentElement.style.getPropertyValue("--app-height")

/** A visualViewport the test can resize, as an on-screen keyboard does. */
function stubViewport(height: number) {
  const listeners = new Set<() => void>()
  const viewport = {
    height,
    addEventListener: (_type: string, listener: () => void) =>
      listeners.add(listener),
    removeEventListener: (_type: string, listener: () => void) =>
      listeners.delete(listener),
  }
  Object.defineProperty(window, "visualViewport", {
    configurable: true,
    value: viewport,
  })
  return {
    listeners,
    resize(next: number) {
      viewport.height = next
      for (const listener of [...listeners]) listener()
    },
  }
}

afterEach(() => {
  cleanup()
  document.documentElement.style.removeProperty("--app-height")
  Object.defineProperty(window, "visualViewport", {
    configurable: true,
    value: undefined,
  })
})

describe("the app height", () => {
  it("follows the visible height, which an on-screen keyboard shrinks", () => {
    const viewport = stubViewport(800)

    render(<Probe active />)
    expect(read()).toBe("800px")

    act(() => viewport.resize(480))
    expect(read()).toBe("480px")
  })

  it("leaves the page's own height alone when not active", () => {
    stubViewport(800)

    render(<Probe active={false} />)

    expect(read()).toBe("")
  })

  it("gives the height back and stops listening when it ends", () => {
    const viewport = stubViewport(800)
    const { unmount } = render(<Probe active />)

    unmount()

    expect(read()).toBe("")
    expect(viewport.listeners.size).toBe(0)
  })

  it("does nothing where there is no visual viewport", () => {
    expect(() => render(<Probe active />)).not.toThrow()
    expect(read()).toBe("")
  })
})
