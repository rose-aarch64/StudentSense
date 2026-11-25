import { useCallback, useEffect, useRef, useState } from "react"

import { readLog, type LogEntry, type RunLog } from "./api"

export const LOG_POLL_MS = 1000

type View = {
  run: number | null
  entries: LogEntry[]
  next: number
  state: RunLog["state"]
}

const EMPTY: View = { run: null, entries: [], next: 0, state: "idle" }

/**
 * The last run's log. It reads once on opening, to show the last run or find
 * one already going, then every second while a run goes on, and once more when
 * the run this window started ends.
 */
export function useCanvasLog(active: boolean) {
  const [view, setView] = useState<View>(EMPTY)
  const latest = useRef(view)
  const reading = useRef(false)
  const mounted = useRef(true)

  const refresh = useCallback(async () => {
    if (reading.current) return
    reading.current = true
    try {
      const read = await readLog(latest.current.run, latest.current.next)
      if (!mounted.current) return
      // A new run sends its whole log; the same run sends only what is new.
      const fresh = read.run === latest.current.run
      const next: View = {
        run: read.run,
        entries: fresh
          ? [...latest.current.entries, ...read.entries]
          : read.entries,
        next: read.next,
        state: read.state,
      }
      latest.current = next
      setView(next)
    } catch {
      // The log is a convenience; a failed read leaves what is shown.
    } finally {
      reading.current = false
    }
  }, [])

  useEffect(() => {
    mounted.current = true
    void refresh()
    return () => {
      mounted.current = false
    }
  }, [refresh])

  const running = active || view.state === "running"
  useEffect(() => {
    if (!running) return
    const timer = setInterval(() => void refresh(), LOG_POLL_MS)
    return () => clearInterval(timer)
  }, [running, refresh])

  const wasActive = useRef(active)
  useEffect(() => {
    if (wasActive.current && !active) void refresh()
    wasActive.current = active
  }, [active, refresh])

  return { entries: view.entries, state: view.state }
}
