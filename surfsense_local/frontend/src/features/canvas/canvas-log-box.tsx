import { useEffect, useRef } from "react"

import { intl } from "@/i18n/intl"
import { cn } from "@/lib/utils"

import { canvasLogText } from "./canvas-log-text"
import { useCanvasLog } from "./use-canvas-log"

/** What the last Sync or Check read and failed on, filling in while one runs. */
export function CanvasLogBox({ active }: { active: boolean }) {
  const { entries, state } = useCanvasLog(active)
  const box = useRef<HTMLDivElement>(null)
  const lines = entries.flatMap((entry) => {
    const words = canvasLogText(entry)
    return words === null ? [] : [{ entry, words }]
  })

  // Keep the newest line in view while a run goes on.
  useEffect(() => {
    if (state === "running" && box.current) {
      box.current.scrollTop = box.current.scrollHeight
    }
  }, [lines.length, state])

  return (
    <section className="flex flex-col gap-1.5">
      <h3 id="canvas-log-title" className="text-sm font-medium">
        {intl.formatMessage({ id: "canvas_log_title", defaultMessage: "Log" })}
      </h3>
      <div
        ref={box}
        role="log"
        aria-labelledby="canvas-log-title"
        className="max-h-56 overflow-y-auto rounded-lg border bg-muted/30 p-2 text-xs"
      >
        {lines.length === 0 ? (
          <p className="text-muted-foreground">
            {intl.formatMessage({
              id: "canvas_log_empty_status",
              defaultMessage:
                "Nothing yet. Press Sync now or Check for changes.",
            })}
          </p>
        ) : (
          <ol className="flex flex-col gap-0.5">
            {lines.map(({ entry, words }) => (
              <li
                key={entry.n}
                data-level={entry.level}
                className={cn(entry.level === "error" && "text-destructive")}
              >
                {words}
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  )
}
