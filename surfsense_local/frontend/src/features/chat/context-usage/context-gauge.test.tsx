import { cleanup, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it } from "vitest"

import { TooltipProvider } from "@/components/ui/tooltip"
import { render } from "@/test-utils"

import type { ContextUsage } from "../api"
import { ContextGauge } from "./context-gauge"
import { contextPercent } from "./context-percent"

afterEach(cleanup)

function show(usage: ContextUsage | null) {
  return render(
    <TooltipProvider>
      <ContextGauge usage={usage} />
    </TooltipProvider>
  )
}

describe("contextPercent", () => {
  it("is the share of the budget spent", () => {
    expect(contextPercent(0, 100)).toBe(0)
    expect(contextPercent(75, 100)).toBe(75)
  })

  it("stops at 100 once the budget is passed", () => {
    expect(contextPercent(140, 100)).toBe(100)
  })

  it("rounds down, so 100 means the budget is reached", () => {
    expect(contextPercent(2, 3)).toBe(66)
    expect(contextPercent(11510, 11560)).toBe(99)
    expect(contextPercent(11560, 11560)).toBe(100)
  })
})

describe("the context gauge", () => {
  it("shows the percentage of the budget spent", () => {
    show({ used: 420, budget: 1000 })

    const gauge = screen.getByRole("button", { name: "History used: 42%" })
    expect(gauge.textContent).toBe("42%")
  })

  it("shows 100% past the budget, not more", () => {
    show({ used: 1400, budget: 1000 })

    expect(screen.getByRole("button").textContent).toBe("100%")
  })

  it("says in its tooltip how many tokens, and what happens at 100%", async () => {
    show({ used: 420, budget: 1000 })

    await userEvent.setup().hover(screen.getByText("42%"))

    const tip = await screen.findByRole("tooltip")
    expect(tip.textContent).toContain("420 of 1,000")
    expect(tip.textContent).toContain("the oldest messages stop being sent")
  })

  it("says in an agent's tooltip that its memory is full at 100%, not that messages stop being sent", async () => {
    render(
      <TooltipProvider>
        <ContextGauge usage={{ used: 6144, budget: 12288 }} agentic />
      </TooltipProvider>
    )

    await userEvent.setup().hover(screen.getByText("50%"))

    const tip = await screen.findByRole("tooltip")
    expect(tip.textContent).toContain("6,144 of 12,288")
    expect(tip.textContent).toContain("its memory is full")
    expect(tip.textContent).toContain("summarize the earlier work")
    expect(tip.textContent).not.toContain("stop being sent")
  })

  it.each([
    ["no usage yet", null],
    ["an unknown window", { used: 5, budget: null }],
    ["a window with no room for history", { used: 5, budget: 0 }],
  ])("shows nothing for %s", (_name, usage) => {
    const { container } = show(usage)

    expect(container.innerHTML).toBe("")
  })
})
