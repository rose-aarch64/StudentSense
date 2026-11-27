import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, renderHook, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { ChatStreamEvent } from "../sse"
import { useContextUsage } from "./use-context-usage"

const mocks = vi.hoisted(() => ({
  frame: undefined as
    | ((threadId: number, event: ChatStreamEvent) => void)
    | undefined,
  getContextUsage: vi.fn(),
}))

vi.mock("../runs/run-store", () => ({
  onRunFrame: (listener: (threadId: number, event: ChatStreamEvent) => void) => {
    mocks.frame = listener
    return () => {
      mocks.frame = undefined
    }
  },
}))

vi.mock("../api", () => ({ getContextUsage: mocks.getContextUsage }))

function setup(threadId: number | null, modelKey: string | null = "small") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
  return renderHook(({ id, model }) => useContextUsage(id, model), {
    wrapper,
    initialProps: { id: threadId, model: modelKey },
  })
}

const usageFrame = (used: number, budget: number | null): ChatStreamEvent => ({
  type: "context-usage",
  used,
  budget,
})

const agentFrame = (type: "agent-step" | "agent-scope"): ChatStreamEvent =>
  ({ type }) as unknown as ChatStreamEvent

describe("context usage", () => {
  beforeEach(() => {
    mocks.getContextUsage.mockReset()
    mocks.getContextUsage.mockImplementation((threadId: number) =>
      Promise.resolve({ used: threadId * 10, budget: 1000 })
    )
  })

  it("starts from the figure the thread was stored with", async () => {
    const { result } = setup(4)

    await waitFor(() => expect(result.current).toEqual({ used: 40, budget: 1000 }))
  })

  it("follows a context-usage frame for its thread", async () => {
    const { result } = setup(4)
    await waitFor(() => expect(result.current).not.toBeNull())

    act(() => mocks.frame?.(4, usageFrame(900, 1000)))

    await waitFor(() =>
      expect(result.current).toEqual({ used: 900, budget: 1000 })
    )
  })

  it("keeps a frame's figure when an older read lands after it", async () => {
    let finishRead: (usage: { used: number; budget: number }) => void = () => {}
    mocks.getContextUsage.mockReturnValueOnce(
      new Promise((resolve) => {
        finishRead = resolve
      })
    )
    const { result } = setup(4)

    await act(async () => {
      mocks.frame?.(4, usageFrame(900, 1000))
    })
    await act(async () => {
      finishRead({ used: 10, budget: 1000 })
    })

    await waitFor(() => expect(result.current?.used).toBe(900))
  })

  it("reads again as an agent works, since its figure comes from the model's own calls", async () => {
    const { result } = setup(4)
    await waitFor(() => expect(result.current?.used).toBe(40))
    mocks.getContextUsage.mockResolvedValueOnce({ used: 7000, budget: 12288 })

    act(() => mocks.frame?.(4, agentFrame("agent-step")))

    await waitFor(() => expect(result.current?.used).toBe(7000), {
      timeout: 3000,
    })
  })

  it("reads again once an agent's reply completes", async () => {
    const { result } = setup(4)
    await waitFor(() => expect(result.current?.used).toBe(40))
    mocks.getContextUsage.mockResolvedValueOnce({ used: 9000, budget: 12288 })

    act(() => mocks.frame?.(4, agentFrame("agent-scope")))
    act(() => mocks.frame?.(4, { type: "completed" } as ChatStreamEvent))

    await waitFor(() => expect(result.current?.used).toBe(9000), {
      timeout: 3000,
    })
  })

  it("does not read again at the end of a chat reply, whose own frames say it exactly", async () => {
    const { result } = setup(4)
    await waitFor(() => expect(result.current?.used).toBe(40))

    act(() => mocks.frame?.(4, usageFrame(900, 1000)))
    act(() => mocks.frame?.(4, { type: "completed" } as ChatStreamEvent))
    await new Promise((resolve) => setTimeout(resolve, 700))

    expect(mocks.getContextUsage).toHaveBeenCalledTimes(1)
    await waitFor(() => expect(result.current?.used).toBe(900))
  })

  it("ignores a frame for another thread", async () => {
    const { result } = setup(4)
    await waitFor(() => expect(result.current).not.toBeNull())

    act(() => mocks.frame?.(5, usageFrame(900, 1000)))

    expect(result.current).toEqual({ used: 40, budget: 1000 })
  })

  it("is null with no thread, and asks for nothing", () => {
    const { result } = setup(null)

    expect(result.current).toBeNull()
    expect(mocks.getContextUsage).not.toHaveBeenCalled()
  })

  it("shows the new thread's figure after switching, never the old one", async () => {
    const { result, rerender } = setup(4)
    await waitFor(() => expect(result.current?.used).toBe(40))

    rerender({ id: 7, model: "small" })

    expect(result.current?.used).not.toBe(40)
    await waitFor(() => expect(result.current?.used).toBe(70))
  })

  it("reads the figure again when another model is chosen, since the budget is its window's", async () => {
    mocks.getContextUsage.mockResolvedValueOnce({ used: 400, budget: 1000 })
    mocks.getContextUsage.mockResolvedValueOnce({ used: 400, budget: 200 })
    const { result, rerender } = setup(4, "large")
    await waitFor(() => expect(result.current?.budget).toBe(1000))

    rerender({ id: 4, model: "small" })

    await waitFor(() => expect(result.current?.budget).toBe(200))
    expect(mocks.getContextUsage).toHaveBeenCalledTimes(2)
  })

  it("does not read twice when it first shows", async () => {
    const { result } = setup(4, "large")
    await waitFor(() => expect(result.current).not.toBeNull())

    expect(mocks.getContextUsage).toHaveBeenCalledTimes(1)
  })

  it("keeps a null budget for a window the model does not report", async () => {
    mocks.getContextUsage.mockResolvedValue({ used: 12, budget: null })
    const { result } = setup(4)

    await waitFor(() => expect(result.current).toEqual({ used: 12, budget: null }))
  })
})
