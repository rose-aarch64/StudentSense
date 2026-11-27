import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { render } from "@/test-utils"

import { AgentPersonaSettings } from "./agent-persona-settings"

function stubAgentPersona(initial: string) {
  let text = initial
  const fetches = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input) !== "/persona/agent") return Response.json({})
      if (init?.method === "PUT") text = JSON.parse(String(init.body)).text
      return Response.json({ text })
    }
  )
  vi.stubGlobal("fetch", fetches)
  return fetches
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe("agent persona settings", () => {
  it("shows the saved agent persona in its own box", async () => {
    stubAgentPersona("Short voice.")
    render(<AgentPersonaSettings />)

    const box = await screen.findByRole("textbox", { name: "Agent persona" })

    await waitFor(() =>
      expect((box as HTMLTextAreaElement).value).toBe("Short voice.")
    )
  })

  it("saves what was typed to the agent's route and says it is saved", async () => {
    const fetches = stubAgentPersona("")
    const user = userEvent.setup()
    render(<AgentPersonaSettings />)

    await user.type(
      await screen.findByRole("textbox", { name: "Agent persona" }),
      "Be brief."
    )
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByText("Saved")).toBeTruthy()
    const put = fetches.mock.calls.find(([, init]) => init?.method === "PUT")
    expect(String(put?.[0])).toBe("/persona/agent")
    expect(JSON.parse(String(put?.[1]?.body))).toEqual({ text: "Be brief." })
  })

  it("keeps Save off until something changed", async () => {
    stubAgentPersona("Short voice.")
    render(<AgentPersonaSettings />)

    await screen.findByRole("textbox", { name: "Agent persona" })

    expect(
      (screen.getByRole("button", { name: "Save" }) as HTMLButtonElement)
        .disabled
    ).toBe(true)
  })
})
