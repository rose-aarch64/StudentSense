import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { render } from "@/test-utils"

import { CanvasSettings } from "./canvas-settings"

type Course = {
  canvas_id: number
  name: string
  workspace_id: number
  refreshed?: string[]
  gone?: string[]
  changed?: string[]
}

type World = {
  connected: boolean
  syncCourses: Course[]
  staleCourses: Course[]
  releaseSync?: () => void
  autoRefresh?: boolean
  refreshedAt?: string | null
  refreshError?: string | null
  log?: {
    run: number
    kind: string | null
    state: string
    entries: LogLine[]
  }
}

type LogLine = {
  n: number
  level: string
  code: string
  params: Record<string, string | number | boolean>
}

/** One log line as the backend sends it. */
function line(
  n: number,
  code: string,
  params: LogLine["params"] = {},
  level = "info"
): LogLine {
  return { n, level, code, params }
}

/** The connection as the backend shows it, with the refresh fields. */
function connectedStatus(world: World) {
  return {
    connected: true,
    base_url: "https://school.example",
    user_name: "Rose B",
    auto_refresh: world.autoRefresh ?? false,
    refreshed_at: world.refreshedAt ?? null,
    refresh_error: world.refreshError ?? null,
  }
}

/** The backend's /canvas routes, in memory; every request is recorded. */
function stubCanvas(world: World, gate?: Promise<void>) {
  async function handle(input: RequestInfo | URL, init?: RequestInit) {
    const path = String(input)
    const method = (init?.method ?? "GET").toUpperCase()
    if (path === "/canvas/connection" && method === "GET") {
      return Response.json(
        world.connected
          ? connectedStatus(world)
          : {
              connected: false,
              base_url: null,
              user_name: null,
              auto_refresh: false,
              refreshed_at: null,
              refresh_error: null,
            }
      )
    }
    if (path === "/canvas/connection" && method === "PATCH") {
      world.autoRefresh = JSON.parse(String(init?.body)).auto_refresh
      return Response.json(connectedStatus(world))
    }
    if (path === "/canvas/connection" && method === "PUT") {
      const body = JSON.parse(String(init?.body))
      if (body.token === "bad") {
        return Response.json(
          {
            detail: {
              code: "canvas_token_refused",
              message: "Canvas did not accept that token",
            },
          },
          { status: 422 }
        )
      }
      world.connected = true
      return Response.json({
        ...connectedStatus(world),
        base_url: `https://${body.base_url}`,
      })
    }
    if (path.startsWith("/canvas/log") && method === "GET") {
      const query = new URL(path, "http://localhost").searchParams
      const after = Number(query.get("after") ?? 0)
      const log = world.log ?? {
        run: 0,
        kind: null,
        state: "idle",
        entries: [],
      }
      const sameRun = query.has("run") && Number(query.get("run")) === log.run
      const entries = sameRun
        ? log.entries.filter((e) => e.n > after)
        : log.entries
      return Response.json({
        ...log,
        entries,
        next: entries.at(-1)?.n ?? (sameRun ? after : 0),
      })
    }
    if (path === "/canvas/connection" && method === "DELETE") {
      world.connected = false
      return new Response(null, { status: 204 })
    }
    if (path === "/canvas/sync" && method === "POST") {
      await gate
      return Response.json({ courses: world.syncCourses })
    }
    if (path === "/canvas/stale" && method === "GET") {
      return Response.json({ courses: world.staleCourses })
    }
    return Response.json([])
  }
  const fetches = vi.fn(handle)
  vi.stubGlobal("fetch", fetches)
  return fetches
}

function course(overrides: Partial<Course> = {}): Course {
  return {
    canvas_id: 1,
    name: "Bio",
    workspace_id: 5,
    refreshed: [],
    gone: [],
    changed: [],
    ...overrides,
  }
}

function world(overrides: Partial<World> = {}): World {
  return { connected: false, syncCourses: [], staleCourses: [], ...overrides }
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe("Canvas settings", () => {
  it("asks for the school's address and a token while nothing is connected", async () => {
    stubCanvas(world())

    render(<CanvasSettings />)

    expect(await screen.findByLabelText("School’s Canvas address")).toBeTruthy()
    expect(screen.getByLabelText("Access token")).toBeTruthy()
    expect(screen.queryByRole("button", { name: "Sync now" })).toBeNull()
  })

  it("connects, then says whose Canvas it is and clears the token from the form", async () => {
    const fetches = stubCanvas(world())
    const user = userEvent.setup()
    render(<CanvasSettings />)

    await user.type(
      await screen.findByLabelText("School’s Canvas address"),
      "school.example"
    )
    await user.type(screen.getByLabelText("Access token"), "good-token")
    await user.click(screen.getByRole("button", { name: "Connect" }))

    expect(
      await screen.findByText("Connected to https://school.example")
    ).toBeTruthy()
    expect(screen.getByText("Signed in as Rose B")).toBeTruthy()
    const put = fetches.mock.calls.find(([, init]) => init?.method === "PUT")
    expect(JSON.parse(String(put?.[1]?.body))).toEqual({
      base_url: "school.example",
      token: "good-token",
    })
    expect(screen.queryByDisplayValue("good-token")).toBeNull()
  })

  it("says so when Canvas does not accept the token, and stays on the form", async () => {
    stubCanvas(world())
    const user = userEvent.setup()
    render(<CanvasSettings />)

    await user.type(
      await screen.findByLabelText("School’s Canvas address"),
      "school.example"
    )
    await user.type(screen.getByLabelText("Access token"), "bad")
    await user.click(screen.getByRole("button", { name: "Connect" }))

    expect(
      await screen.findByText("Canvas did not accept that token.")
    ).toBeTruthy()
    expect(screen.getByRole("button", { name: "Connect" })).toBeTruthy()
  })

  it("syncs and says what it did", async () => {
    stubCanvas(
      world({
        connected: true,
        syncCourses: [
          course({ refreshed: ["Week1.pdf"], gone: ["Old.pdf"] }),
          course({ canvas_id: 2, name: "Chem", workspace_id: 6 }),
        ],
      })
    )
    const user = userEvent.setup()
    render(<CanvasSettings />)

    await user.click(await screen.findByRole("button", { name: "Sync now" }))

    expect(await screen.findByText("Synced 2 classes.")).toBeTruthy()
    expect(screen.getByText("Updated: Week1.pdf")).toBeTruthy()
    expect(screen.getByText("No longer in Canvas: Old.pdf")).toBeTruthy()
  })

  it("holds the Sync button while a sync runs, since it can take minutes", async () => {
    let release: () => void = () => {}
    const gate = new Promise<void>((resolve) => {
      release = resolve
    })
    stubCanvas(world({ connected: true, syncCourses: [course()] }), gate)
    const user = userEvent.setup()
    render(<CanvasSettings />)

    await user.click(await screen.findByRole("button", { name: "Sync now" }))

    // A spinner joins the button's name while it works.
    await waitFor(() =>
      expect(
        (screen.getByRole("button", { name: /Sync now/ }) as HTMLButtonElement)
          .disabled
      ).toBe(true)
    )
    release()
    expect(await screen.findByText("Synced 1 class.")).toBeTruthy()
  })

  it("lists what changed in Canvas when asked to check", async () => {
    stubCanvas(
      world({
        connected: true,
        staleCourses: [course({ changed: ["Week1.pdf", "Week2.pdf"] })],
      })
    )
    const user = userEvent.setup()
    render(<CanvasSettings />)

    await user.click(
      await screen.findByRole("button", { name: "Check for changes" })
    )

    expect(
      await screen.findByText("Changed in Canvas: Week1.pdf and Week2.pdf")
    ).toBeTruthy()
  })

  it("says when everything matches", async () => {
    stubCanvas(world({ connected: true, staleCourses: [course()] }))
    const user = userEvent.setup()
    render(<CanvasSettings />)

    await user.click(
      await screen.findByRole("button", { name: "Check for changes" })
    )

    expect(await screen.findByText("Everything matches Canvas.")).toBeTruthy()
  })

  it("disconnects and goes back to the form", async () => {
    stubCanvas(world({ connected: true }))
    const user = userEvent.setup()
    render(<CanvasSettings />)

    await user.click(await screen.findByRole("button", { name: "Disconnect" }))

    expect(await screen.findByLabelText("Access token")).toBeTruthy()
  })

  it("shows the refresh switch off for a connection that has not turned it on", async () => {
    stubCanvas(world({ connected: true }))
    render(<CanvasSettings />)

    const toggle = await screen.findByRole("switch", {
      name: "Keep my to-do list up to date",
    })

    expect(toggle.getAttribute("aria-checked")).toBe("false")
    expect(screen.queryByText(/^Last updated/)).toBeNull()
    expect(screen.queryByText("Not updated yet.")).toBeNull()
  })

  it("turns the refresh on and sends the change", async () => {
    const fetches = stubCanvas(world({ connected: true }))
    const user = userEvent.setup()
    render(<CanvasSettings />)

    const toggle = await screen.findByRole("switch", {
      name: "Keep my to-do list up to date",
    })
    await user.click(toggle)

    await waitFor(() =>
      expect(toggle.getAttribute("aria-checked")).toBe("true")
    )
    const patch = fetches.mock.calls.find(
      ([, init]) => init?.method === "PATCH"
    )
    expect(JSON.parse(String(patch?.[1]?.body))).toEqual({ auto_refresh: true })
  })

  it("shows when the refresh last ran", async () => {
    stubCanvas(
      world({
        connected: true,
        autoRefresh: true,
        refreshedAt: "2026-11-25T14:00:00Z",
      })
    )
    render(<CanvasSettings />)

    expect(await screen.findByText(/^Last updated/)).toBeTruthy()
  })

  it("says it has not updated yet when it never ran", async () => {
    stubCanvas(world({ connected: true, autoRefresh: true }))
    render(<CanvasSettings />)

    expect(await screen.findByText("Not updated yet.")).toBeTruthy()
  })

  it("explains a failed refresh in words", async () => {
    stubCanvas(
      world({
        connected: true,
        autoRefresh: true,
        refreshError: "canvas_token_refused",
      })
    )
    render(<CanvasSettings />)

    expect(
      await screen.findByText("Canvas did not accept that token.")
    ).toBeTruthy()
  })

  it("names a school switched off in Settings when the refresh was refused", async () => {
    stubCanvas(
      world({
        connected: true,
        autoRefresh: true,
        refreshError: "egress_disabled",
      })
    )
    render(<CanvasSettings />)

    expect(
      await screen.findByText("Canvas is switched off in Settings › Network.")
    ).toBeTruthy()
  })

  it("says nothing yet before any run", async () => {
    stubCanvas(world({ connected: true }))
    render(<CanvasSettings />)

    expect(
      await screen.findByText(
        "Nothing yet. Press Sync now or Check for changes."
      )
    ).toBeTruthy()
  })

  it("shows the last run's lines when opened", async () => {
    stubCanvas(
      world({
        connected: true,
        log: {
          run: 1,
          kind: "sync",
          state: "done",
          entries: [
            line(1, "sync_started"),
            line(2, "class_started", { name: "Bio" }),
            line(3, "class_read", {
              name: "Bio",
              assignments: 2,
              announcements: 1,
              modules: 1,
              pages: 1,
              files: 1,
            }),
            line(4, "file_kept", { name: "Week1.pdf" }),
            line(5, "finished", { classes: 1, errors: 0 }),
          ],
        },
      })
    )
    render(<CanvasSettings />)

    expect(await screen.findByText("Sync started")).toBeTruthy()
    expect(screen.getByText("Reading Bio…")).toBeTruthy()
    expect(
      screen.getByText(
        "Read 2 assignments, 1 announcement, 1 module, 1 page and 1 file."
      )
    ).toBeTruthy()
    expect(screen.getByText("Kept Week1.pdf")).toBeTruthy()
    expect(screen.getByText("Done: 1 class, no errors.")).toBeTruthy()
  })

  it("fills in while a sync runs and stops polling once it ends", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    let release: () => void = () => {}
    const gate = new Promise<void>((resolve) => {
      release = resolve
    })
    const w = world({ connected: true, syncCourses: [course()] })
    const fetches = stubCanvas(w, gate)
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    render(<CanvasSettings />)

    await user.click(await screen.findByRole("button", { name: "Sync now" }))
    w.log = {
      run: 1,
      kind: "sync",
      state: "running",
      entries: [line(1, "sync_started")],
    }
    await vi.advanceTimersByTimeAsync(1000)
    expect(await screen.findByText("Sync started")).toBeTruthy()

    w.log.entries.push(line(2, "class_started", { name: "Bio" }))
    await vi.advanceTimersByTimeAsync(1000)
    expect(await screen.findByText("Reading Bio…")).toBeTruthy()

    w.log.state = "done"
    w.log.entries.push(line(3, "finished", { classes: 1, errors: 0 }))
    release()
    expect(await screen.findByText("Done: 1 class, no errors.")).toBeTruthy()

    const polls = () =>
      fetches.mock.calls.filter(([url]) =>
        String(url).startsWith("/canvas/log")
      ).length
    const settled = polls()
    await vi.advanceTimersByTimeAsync(3000)
    expect(polls()).toBe(settled)
    vi.useRealTimers()
  })

  it("finds a run already going when the page opens", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const w = world({
      connected: true,
      log: {
        run: 1,
        kind: "sync",
        state: "running",
        entries: [line(1, "sync_started")],
      },
    })
    stubCanvas(w)
    render(<CanvasSettings />)
    expect(await screen.findByText("Sync started")).toBeTruthy()

    w.log!.state = "done"
    w.log!.entries.push(line(2, "finished", { classes: 0, errors: 0 }))
    await vi.advanceTimersByTimeAsync(1000)

    expect(await screen.findByText("Done: 0 classes, no errors.")).toBeTruthy()
    vi.useRealTimers()
  })

  it("marks an error line", async () => {
    stubCanvas(
      world({
        connected: true,
        log: {
          run: 1,
          kind: "sync",
          state: "done",
          entries: [line(1, "file_failed", { name: "Week2.pdf" }, "error")],
        },
      })
    )
    render(<CanvasSettings />)

    const failed = await screen.findByText("Could not fetch Week2.pdf.")

    expect(failed.closest("[data-level]")?.getAttribute("data-level")).toBe(
      "error"
    )
  })

  it("says why a run stopped in words", async () => {
    stubCanvas(
      world({
        connected: true,
        log: {
          run: 1,
          kind: "sync",
          state: "failed",
          entries: [
            line(1, "stopped", { error: "canvas_token_refused" }, "error"),
          ],
        },
      })
    )
    render(<CanvasSettings />)

    expect(
      await screen.findByText("Stopped: Canvas did not accept that token.")
    ).toBeTruthy()
  })

  it("shows a name with braces and tags as plain text", async () => {
    stubCanvas(
      world({
        connected: true,
        log: {
          run: 1,
          kind: "sync",
          state: "running",
          entries: [line(1, "class_started", { name: "Bio {count} <b>1</b>" })],
        },
      })
    )
    render(<CanvasSettings />)

    expect(
      await screen.findByText("Reading Bio {count} <b>1</b>…")
    ).toBeTruthy()
  })

  it("ignores a code it does not know", async () => {
    stubCanvas(
      world({
        connected: true,
        log: {
          run: 1,
          kind: "sync",
          state: "done",
          entries: [line(1, "future_code"), line(2, "sync_started")],
        },
      })
    )
    render(<CanvasSettings />)

    await screen.findByText("Sync started")
    const region = screen.getByRole("log", { name: "Log" })

    expect(within(region).getAllByRole("listitem")).toHaveLength(1)
  })
})
