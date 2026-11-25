import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { render } from "@/test-utils"

import type { Board, Todo } from "./api"
import { TodoDialog } from "./todo-dialog"

function task(overrides: Partial<Todo> = {}): Todo {
  return {
    id: 1,
    workspace_id: null,
    title: "Read ch. 4",
    due_at: null,
    done_at: null,
    done: false,
    source: "manual",
    source_key: null,
    created_at: "2026-11-24T00:00:00Z",
    updated_at: "2026-11-24T00:00:00Z",
    ...overrides,
  }
}

const WEEK = 7 * 86_400_000

/** A rough stand-in for the backend's sections: enough to render, not to bucket. */
function boardOf(tasks: Todo[]): Board {
  const now = Date.now()
  const open = tasks.filter((t) => !t.done)
  const due = (t: Todo) => (t.due_at ? new Date(t.due_at).getTime() : null)
  const late = (t: Todo) => (due(t) ?? now) < now
  return {
    today: "2026-11-24",
    overdue: open.filter((t) => late(t) && now - (due(t) ?? now) <= WEEK),
    this_week: [
      {
        date: "2026-11-24",
        today: true,
        todos: open.filter((t) => due(t) !== null && !late(t)),
      },
    ],
    next_week: [],
    in_two_weeks: [],
    future: [],
    undated: open.filter((t) => t.due_at === null),
    done: tasks.filter((t) => t.done),
    older: open.filter((t) => late(t) && now - (due(t) ?? now) > WEEK),
  }
}

/** The backend's /todos routes, kept in memory; every request is recorded. */
function stubTodos(initial: Todo[]) {
  let tasks = [...initial]
  let nextId = 100
  async function handle(input: RequestInfo | URL, init?: RequestInit) {
    const path = String(input)
    const method = (init?.method ?? "GET").toUpperCase()
    if (path === "/todos/board") return Response.json(boardOf(tasks))
    if (path === "/todos" && method === "GET") return Response.json(tasks)
    if (path === "/todos" && method === "POST") {
      const body = JSON.parse(String(init?.body))
      const created = task({
        id: nextId++,
        title: body.title,
        due_at: body.due_at ?? null,
      })
      tasks = [...tasks, created]
      return Response.json(created, { status: 201 })
    }
    const one = path.match(/^\/todos\/(\d+)$/)
    if (one && method === "PATCH") {
      const body = JSON.parse(String(init?.body))
      tasks = tasks.map((t) =>
        t.id === Number(one[1])
          ? {
              ...t,
              done: body.done,
              done_at: body.done ? "2026-11-24T12:00:00Z" : null,
            }
          : t
      )
      return Response.json(tasks.find((t) => t.id === Number(one[1])))
    }
    if (one && method === "DELETE") {
      tasks = tasks.filter((t) => t.id !== Number(one[1]))
      return new Response(null, { status: 204 })
    }
    return Response.json([])
  }
  const fetches = vi.fn(handle)
  vi.stubGlobal("fetch", fetches)
  return fetches
}

/** The bodies of every request this test made with `method`, in order. */
function sentBodies(fetches: ReturnType<typeof stubTodos>, method: string) {
  return fetches.mock.calls
    .filter(([, init]) => init?.method === method)
    .map(([, init]) => JSON.parse(String(init?.body)))
}

/** The body of the one request this test made with `method`. */
function sentBody(fetches: ReturnType<typeof stubTodos>, method: string) {
  return sentBodies(fetches, method)[0]
}

function renderDialog() {
  return render(<TodoDialog open onOpenChange={() => {}} />)
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

/** A matchMedia that answers true for the compact query while `compact` holds. */
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

describe("to-do dialog", () => {
  it("fills the screen when the layout is compact", async () => {
    stubMedia(true)
    stubTodos([])

    renderDialog()

    const dialog = await screen.findByRole("dialog", { name: "To-do" })
    expect(dialog.className).toContain("h-dvh")
    expect(dialog.className).toContain("w-screen")
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      value: undefined,
    })
  })

  it("keeps its card size when it is not compact", async () => {
    stubMedia(false)
    stubTodos([])

    renderDialog()

    const dialog = await screen.findByRole("dialog", { name: "To-do" })
    expect(dialog.className).toContain("sm:max-w-md")
    expect(dialog.className).not.toContain("h-dvh")
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      value: undefined,
    })
  })

  it("lists the tasks the backend returns", async () => {
    stubTodos([
      task({ id: 1, title: "Read ch. 4" }),
      task({ id: 2, title: "Lab 1 report" }),
    ])
    // Undated tasks are listed as they come.

    renderDialog()

    expect(await screen.findByText("Read ch. 4")).toBeTruthy()
    expect(screen.getByText("Lab 1 report")).toBeTruthy()
  })

  it("says so when there is nothing to do", async () => {
    stubTodos([])

    renderDialog()

    expect(await screen.findByText("Nothing to do")).toBeTruthy()
  })

  it("adds a task from the box and shows it", async () => {
    const fetches = stubTodos([])
    const user = userEvent.setup()
    renderDialog()

    await user.type(
      await screen.findByPlaceholderText("Add a task"),
      "Buy lab goggles"
    )
    await user.click(screen.getByRole("button", { name: "Add" }))

    expect(await screen.findByText("Buy lab goggles")).toBeTruthy()
    expect(sentBody(fetches, "POST")).toEqual({ title: "Buy lab goggles" })
  })

  it("checks a task off and lets it be unchecked again", async () => {
    const fetches = stubTodos([task({ id: 1, title: "Read ch. 4" })])
    const user = userEvent.setup()
    renderDialog()

    await user.click(
      await screen.findByRole("checkbox", { name: "Read ch. 4" })
    )

    // A finished task moves to Done, which stays closed until opened.
    await user.click(await screen.findByRole("button", { name: /Done/ }))
    expect(
      screen
        .getByRole("checkbox", { name: "Read ch. 4" })
        .getAttribute("aria-checked")
    ).toBe("true")

    await user.click(screen.getByRole("checkbox", { name: "Read ch. 4" }))

    await waitFor(() =>
      expect(sentBodies(fetches, "PATCH")).toEqual([
        { done: true },
        { done: false },
      ])
    )
  })

  it("never hands fetch anything but a real AbortSignal as a signal", async () => {
    // A browser's fetch throws on any other value, which a stub would not.
    const fetches = stubTodos([task({ id: 1, title: "Read ch. 4" })])
    const user = userEvent.setup()
    renderDialog()

    await user.type(
      await screen.findByPlaceholderText("Add a task"),
      "Buy lab goggles"
    )
    await user.click(screen.getByRole("button", { name: "Add" }))
    await screen.findByText("Buy lab goggles")
    await user.click(screen.getByRole("button", { name: "Delete Read ch. 4" }))
    await waitFor(() => expect(screen.queryByText("Read ch. 4")).toBeNull())

    const mutations = fetches.mock.calls.filter(
      ([, init]) => init?.method === "POST" || init?.method === "DELETE"
    )
    expect(mutations).toHaveLength(2)
    for (const [, init] of mutations) {
      expect(init?.signal == null || init.signal instanceof AbortSignal).toBe(
        true
      )
    }
  })

  it("deletes a task from its row", async () => {
    const fetches = stubTodos([
      task({ id: 1, title: "Read ch. 4" }),
      task({ id: 2, title: "Lab 1 report" }),
    ])
    const user = userEvent.setup()
    renderDialog()

    await user.click(
      await screen.findByRole("button", { name: "Delete Read ch. 4" })
    )

    await waitFor(() => expect(screen.queryByText("Read ch. 4")).toBeNull())
    expect(screen.getByText("Lab 1 report")).toBeTruthy()
    expect(
      fetches.mock.calls.some(
        ([url, init]) => url === "/todos/1" && init?.method === "DELETE"
      )
    ).toBe(true)
  })

  it("sends the due date picked, as the end of that day on the user's clock", async () => {
    const fetches = stubTodos([])
    const user = userEvent.setup()
    renderDialog()

    await user.type(
      await screen.findByPlaceholderText("Add a task"),
      "Lab 1 report"
    )
    fireEvent.change(screen.getByLabelText("Due date"), {
      target: { value: "2026-12-01" },
    })
    await user.click(screen.getByRole("button", { name: "Add" }))

    await screen.findByText("Lab 1 report")
    const due = new Date(sentBody(fetches, "POST").due_at)
    expect([due.getFullYear(), due.getMonth() + 1, due.getDate()]).toEqual([
      2026, 12, 1,
    ])
  })
})

describe("to-do dialog and old tasks", () => {
  const daysAgo = (days: number) =>
    new Date(Date.now() - days * 86_400_000).toISOString()

  it("hides tasks due long ago until asked", async () => {
    stubTodos([
      task({ id: 1, title: "Read ch. 4", due_at: daysAgo(-3) }),
      task({ id: 2, title: "Orientation quiz", due_at: daysAgo(800) }),
      task({ id: 3, title: "Undated task" }),
    ])
    const user = userEvent.setup()
    renderDialog()

    expect(await screen.findByText("Read ch. 4")).toBeTruthy()
    expect(screen.getByText("Undated task")).toBeTruthy()
    expect(screen.queryByText("Orientation quiz")).toBeNull()

    await user.click(screen.getByRole("button", { name: "Show 1 older" }))

    expect(screen.getByText("Orientation quiz")).toBeTruthy()
    expect(screen.getByRole("button", { name: "Hide older" })).toBeTruthy()
  })

  it("sets aside, and does not offer to delete, what is long overdue", async () => {
    const fetches = stubTodos([
      task({ id: 2, title: "Orientation quiz", due_at: daysAgo(800) }),
    ])
    renderDialog()

    await screen.findByRole("button", { name: "Show 1 older" })

    expect(
      fetches.mock.calls.some(([, init]) => init?.method === "DELETE")
    ).toBe(false)
  })
})

describe("to-do dialog sections", () => {
  const daysAgo = (days: number) =>
    new Date(Date.now() - days * 86_400_000).toISOString()

  it("names each section and hides the empty ones", async () => {
    stubTodos([
      task({ id: 1, title: "Missed quiz", due_at: daysAgo(2) }),
      task({ id: 2, title: "Lab tonight", due_at: daysAgo(-0.1) }),
      task({ id: 3, title: "Someday" }),
    ])
    renderDialog()

    expect(await screen.findByText("Lab tonight")).toBeTruthy()

    expect(screen.getByRole("button", { name: /Overdue/ })).toBeTruthy()
    expect(screen.getByRole("heading", { name: "This week" })).toBeTruthy()
    expect(screen.getByRole("heading", { name: "No due date" })).toBeTruthy()
    expect(screen.queryByRole("heading", { name: "Next week" })).toBeNull()
    expect(screen.queryByRole("button", { name: /Done/ })).toBeNull()
  })

  it("marks today in this week, and opens Overdue but not Done", async () => {
    stubTodos([
      task({ id: 1, title: "Missed quiz", due_at: daysAgo(2) }),
      task({ id: 2, title: "Finished essay", done: true, done_at: daysAgo(1) }),
    ])
    const user = userEvent.setup()
    renderDialog()

    expect(await screen.findByText("Missed quiz")).toBeTruthy()
    expect(screen.getByText("Today")).toBeTruthy()
    expect(screen.queryByText("Finished essay")).toBeNull()

    await user.click(screen.getByRole("button", { name: /Done/ }))

    expect(screen.getByText("Finished essay")).toBeTruthy()
  })
})
