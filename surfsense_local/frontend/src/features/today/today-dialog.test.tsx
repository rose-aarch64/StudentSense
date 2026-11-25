import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { render } from "@/test-utils"

import { TodayDialog } from "./today-dialog"

/** The backend's /today/ask, answering from a script; every body sent is kept. */
function stubAsk(replies: Array<string | number>) {
  const bodies: Array<Record<string, unknown>> = []
  vi.stubGlobal(
    "fetch",
    vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      bodies.push(JSON.parse(String(init?.body)))
      const next = replies.shift() ?? "…"
      if (typeof next === "string") return Response.json({ text: next })
      return Response.json(
        { detail: "no chat model selected" },
        { status: next }
      )
    })
  )
  return bodies
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe("the Today window", () => {
  it("asks the day's question in one press and shows the answer", async () => {
    const bodies = stubAsk(["Lab 1 is due tonight."])
    const user = userEvent.setup()
    render(<TodayDialog open onOpenChange={() => {}} />)

    await user.click(
      screen.getByRole("button", { name: "What’s going on today?" })
    )

    expect(await screen.findByText("Lab 1 is due tonight.")).toBeTruthy()
    expect(bodies[0].text).toBe("What’s going on today?")
    // The user's own zone goes with it: the server cannot know which day it is.
    expect(String(bodies[0].now)).toMatch(/[+-]\d\d:\d\d$/)
  })

  it("sends the conversation so far with each question", async () => {
    const bodies = stubAsk(["Nothing due.", "Tomorrow is free."])
    const user = userEvent.setup()
    render(<TodayDialog open onOpenChange={() => {}} />)

    const box = screen.getByRole("textbox", { name: "Ask about today" })
    await user.type(box, "today?{Enter}")
    await screen.findByText("Nothing due.")
    await user.type(box, "and tomorrow?{Enter}")

    expect(await screen.findByText("Tomorrow is free.")).toBeTruthy()
    expect(bodies[1].history).toEqual([
      { role: "user", text: "today?" },
      { role: "assistant", text: "Nothing due." },
    ])
  })

  it("says to pick a chat model when there is none", async () => {
    stubAsk([409])
    const user = userEvent.setup()
    render(<TodayDialog open onOpenChange={() => {}} />)

    await user.type(
      screen.getByRole("textbox", { name: "Ask about today" }),
      "today?{Enter}"
    )

    expect(
      await screen.findByText("Choose a chat model in Settings first.")
    ).toBeTruthy()
  })
})
