import type { ComponentProps } from "react"

import { cn } from "@/lib/utils"

import { useCompactLayout } from "./use-compact-layout"

/**
 * The window's grid: the workspace rail, then the columns. Shared with the
 * startup frame, so the dashboard's first frame lands on the frame's lines.
 *
 * The rail is 216 px, a row each for icon and name. The minimum window width,
 * 73rem beside the old 56 px rail, grows by the 160 px difference. Written out
 * in full because Tailwind reads class names, not expressions.
 *
 * Narrower than the desktop layout can fit, it is one column with no minimum:
 * the rail then lives in the sidebar's sheet.
 */
export function DashboardShell({
  className,
  ...props
}: ComponentProps<"main">) {
  const compact = useCompactLayout()
  return (
    <main
      className={cn(
        "relative grid h-full overflow-hidden bg-app-shell",
        compact
          ? "min-w-0 grid-cols-1"
          : "min-w-[calc(73rem+160px)] grid-cols-[216px_minmax(0,1fr)]",
        className
      )}
      {...props}
    />
  )
}
