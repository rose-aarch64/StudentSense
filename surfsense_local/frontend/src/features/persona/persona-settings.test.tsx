import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { render } from "@/test-utils"

import { PersonaSettings } from "./persona-settings"

function stubPersona(initial: string) {
  let text = initial
  const fetches = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input) !== "/persona") return Response.json({})
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

describe("persona settings", () => {
  it("shows the saved persona in a box", async () => {
    stubPersona("Call me Rose.")
    render(<PersonaSettings />)

    const box = await screen.findByRole("textbox", { name: "Persona" })

    await waitFor(() =>
      expect((box as HTMLTextAreaElement).value).toBe("Call me Rose.")
    )
  })

  it("saves what was typed and says it is saved", async () => {
    const fetches = stubPersona("")
    const user = userEvent.setup()
    render(<PersonaSettings />)

    await user.type(
      await screen.findByRole("textbox", { name: "Persona" }),
      "Be brief."
    )
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByText("Saved")).toBeTruthy()
    const put = fetches.mock.calls.find(([, init]) => init?.method === "PUT")
    expect(JSON.parse(String(put?.[1]?.body))).toEqual({ text: "Be brief." })
  })

  it("keeps Save off until something changed", async () => {
    stubPersona("Be brief.")
    render(<PersonaSettings />)

    await screen.findByRole("textbox", { name: "Persona" })

    expect(
      (screen.getByRole("button", { name: "Save" }) as HTMLButtonElement)
        .disabled
    ).toBe(true)
  })
})
