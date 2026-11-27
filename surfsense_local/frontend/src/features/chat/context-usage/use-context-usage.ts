import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useRef } from "react"

import { getContextUsage, type ContextUsage } from "../api"
import { chatKeys } from "../query-keys"
import { onRunFrame } from "../runs/run-store"

// The frames only an agent's turn sends.
const AGENT_FRAMES = new Set(["agent-preparing", "agent-scope", "agent-step"])
// Steps come fast, so a burst of them makes one read.
const AGENT_READ_DELAY_MS = 300

/**
 * How full a thread's history is: what it was stored with, then what each
 * reply's frames say. Null with no thread, and while the first read is out.
 * `modelKey` names the selected model: the budget is its window's, so a
 * different one reads the figure again.
 */
export function useContextUsage(
  threadId: number | null,
  modelKey: string | null = null
): ContextUsage | null {
  const client = useQueryClient()
  const shownFor = useRef(modelKey)

  useEffect(() => {
    if (shownFor.current === modelKey) return
    shownFor.current = modelKey
    void client.invalidateQueries({
      queryKey: [...chatKeys.all, "context-usage"],
    })
  }, [client, modelKey])

  useEffect(() => {
    // An agent's figure is not in its frames: the server keeps the size of the
    // prompt of each model call, so it is read again as the agent works. A
    // chat's frames say it exactly, and a read would only replace that.
    const agentRuns = new Set<number>()
    const timers = new Map<number, ReturnType<typeof setTimeout>>()
    const readSoon = (threadId: number) => {
      clearTimeout(timers.get(threadId))
      timers.set(
        threadId,
        setTimeout(() => {
          timers.delete(threadId)
          void client.invalidateQueries({
            queryKey: chatKeys.contextUsage(threadId),
          })
        }, AGENT_READ_DELAY_MS)
      )
    }
    const stop = onRunFrame((frameThreadId, event) => {
      if (event.type === "context-usage") {
        // Kept for any thread, so one answering in the background is right
        // when its tab is opened. A read still out would land after it and
        // win with an older figure, so it is called off first.
        const key = chatKeys.contextUsage(frameThreadId)
        void client.cancelQueries({ queryKey: key }).then(() =>
          client.setQueryData<ContextUsage>(key, {
            used: event.used,
            budget: event.budget,
          })
        )
      } else if (AGENT_FRAMES.has(event.type)) {
        agentRuns.add(frameThreadId)
        if (event.type === "agent-step") readSoon(frameThreadId)
      } else if (
        (event.type === "completed" || event.type === "done") &&
        agentRuns.has(frameThreadId)
      ) {
        readSoon(frameThreadId)
        if (event.type === "done") agentRuns.delete(frameThreadId)
      }
    })
    return () => {
      stop()
      for (const timer of timers.values()) clearTimeout(timer)
    }
  }, [client])

  const query = useQuery({
    queryKey: chatKeys.contextUsage(threadId ?? -1),
    queryFn: ({ signal }) =>
      threadId === null
        ? Promise.reject(new Error("no thread"))
        : getContextUsage(threadId, signal),
    enabled: threadId !== null,
  })
  return threadId === null ? null : (query.data ?? null)
}
