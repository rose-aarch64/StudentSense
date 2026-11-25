import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { act, cleanup, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { TooltipProvider } from "@/components/ui/tooltip"
import { render } from "@/test-utils"

import { DashboardPage } from "./dashboard-page"

const first = {
  id: 1,
  name: "My Workspace",
  created_at: "2026-09-05T00:00:00Z",
  updated_at: "2026-09-05T00:00:00Z",
}
const second = { ...first, id: 2, name: "Second Workspace" }

/** A matchMedia that answers true for the compact query while `compact` holds. */
function stubMedia(compact: boolean) {
  const listeners = new Set<() => void>()
  const state = { compact }
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: vi.fn((query: string) => ({
      media: query,
      get matches() {
        return state.compact && query === "(max-width: 1023px)"
      },
      addEventListener: (_type: string, listener: () => void) =>
        listeners.add(listener),
      removeEventListener: (_type: string, listener: () => void) =>
        listeners.delete(listener),
    })),
  })
  return {
    set(next: boolean) {
      state.compact = next
      for (const listener of [...listeners]) listener()
    },
  }
}

const TODOS = {
  today: "2026-11-25",
  overdue: [],
  this_week: [],
  next_week: [],
  in_two_weeks: [],
  future: [],
  undated: [],
  done: [],
  older: [],
}

function phoneServer() {
  return vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input)
    if (path === "/llm/providers") {
      return Response.json([
        { name: "llamacpp", healthy: true, can_download: true },
      ])
    }
    if (path.startsWith("/todos")) return Response.json(TODOS)
    if (path === "/workspace-folders") return Response.json([])
    if (path.includes("/chat/threads")) return Response.json([])
    if (path.includes("/documents?")) return Response.json([])
    return Response.json({ detail: "not found" }, { status: 404 })
  })
}

function page() {
  return render(
    <TooltipProvider>
      <DashboardPage
        initialProviderAvailable={true}
        selection={{
          model_type: "text_gen",
          provider: "llamacpp",
          connection_id: null,
          name: "llama3.2:1b",
          updated_at: "2026-09-05T00:00:00Z",
        }}
        initialWorkspaces={[first, second]}
        onModelSelected={vi.fn()}
      />
    </TooltipProvider>
  )
}

beforeEach(() => {
  localStorage.clear()
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
  )
  Object.defineProperty(HTMLElement.prototype, "scrollTo", {
    configurable: true,
    value: vi.fn(),
  })
  Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
    configurable: true,
    value: vi.fn(),
  })
  vi.stubGlobal("surfsense", {
    apiUrl: "",
    platform: "darwin",
    openDocument: vi.fn(async () => ""),
    revealDocument: vi.fn(async () => ""),
  })
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: undefined,
  })
})

describe("the dashboard on a phone", () => {
  it("shows the chat with a menu button and no rail beside it", async () => {
    stubMedia(true)
    vi.stubGlobal("fetch", phoneServer())

    page()

    await screen.findByRole("textbox", { name: "Message" })
    expect(screen.getByRole("button", { name: "Open menu" })).toBeTruthy()
    expect(screen.queryByRole("navigation", { name: "Workspaces" })).toBeNull()
  })

  it("opens the workspaces, chats and sources from the menu", async () => {
    stubMedia(true)
    vi.stubGlobal("fetch", phoneServer())
    page()
    await screen.findByRole("textbox", { name: "Message" })

    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Open menu" }))

    const menu = screen.getByRole("dialog", { name: "Menu" })
    expect(
      within(menu).getByRole("navigation", { name: "Workspaces" })
    ).toBeTruthy()
    expect(within(menu).getByRole("button", { name: "New chat" })).toBeTruthy()
    expect(within(menu).getByRole("button", { name: "Chats" })).toBeTruthy()
  })

  it("switches workspace from the menu and closes it", async () => {
    stubMedia(true)
    const fetchMock = phoneServer()
    vi.stubGlobal("fetch", fetchMock)
    const user = userEvent.setup()
    page()
    await screen.findByRole("textbox", { name: "Message" })
    await user.click(screen.getByRole("button", { name: "Open menu" }))

    await user.click(
      within(screen.getByRole("dialog", { name: "Menu" })).getByRole("button", {
        name: "Second Workspace",
      })
    )

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/workspaces/2/chat/threads",
        expect.anything()
      )
    )
    expect(screen.queryByRole("dialog", { name: "Menu" })).toBeNull()
  })

  it("closes the menu after New chat", async () => {
    stubMedia(true)
    vi.stubGlobal("fetch", phoneServer())
    const user = userEvent.setup()
    page()
    await screen.findByRole("textbox", { name: "Message" })
    await user.click(screen.getByRole("button", { name: "Open menu" }))

    await user.click(
      within(screen.getByRole("dialog", { name: "Menu" })).getByRole("button", {
        name: "New chat",
      })
    )

    expect(screen.queryByRole("dialog", { name: "Menu" })).toBeNull()
  })

  it("opens the to-do list from the chat's header", async () => {
    stubMedia(true)
    vi.stubGlobal("fetch", phoneServer())
    page()
    await screen.findByRole("textbox", { name: "Message" })

    const todo = screen.getByRole("button", { name: "To-do" })
    // The chat's own button, not the sidebar's row, which sits in the closed menu.
    expect(todo.closest("aside")).toBeNull()

    await userEvent.setup().click(todo)

    expect(await screen.findByRole("dialog", { name: "To-do" })).toBeTruthy()
  })

  it("keeps the workspace and the chat when the window crosses the breakpoint", async () => {
    const media = stubMedia(true)
    vi.stubGlobal("fetch", phoneServer())
    page()
    await screen.findByRole("textbox", { name: "Message" })

    act(() => media.set(false))

    expect(screen.queryByRole("button", { name: "Open menu" })).toBeNull()
    const rail = screen.getByRole("navigation", { name: "Workspaces" })
    expect(
      within(rail)
        .getByRole("button", { name: "My Workspace" })
        .getAttribute("aria-current")
    ).toBe("page")
    expect(screen.getByRole("textbox", { name: "Message" })).toBeTruthy()
  })
})

describe("the dashboard on a desktop", () => {
  it("shows the rail and the resize edges, and no menu button", async () => {
    stubMedia(false)
    vi.stubGlobal("fetch", phoneServer())

    page()

    await screen.findByRole("textbox", { name: "Message" })
    expect(screen.getByRole("navigation", { name: "Workspaces" })).toBeTruthy()
    expect(screen.queryByRole("button", { name: "Open menu" })).toBeNull()
    expect(screen.getByLabelText("Resize sidebar")).toBeTruthy()
  })
})
