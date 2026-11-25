import { useEffect, type ReactNode } from "react"

import { Button } from "@/components/ui/button"
import { XIcon } from "@/components/ui/icons"
import { cn } from "@/lib/utils"

/**
 * A full-screen layer over the chat, for the phone's drawer and detail panel.
 * Its children stay mounted while it is closed, so a list keeps its scroll; it
 * is then inert, hidden from assistive technology and moved off the screen.
 */
export function CompactSheet({
  open,
  side,
  label,
  closeLabel,
  onClose,
  children,
}: {
  open: boolean
  side: "start" | "end"
  // The sheet's accessible name, and its close button's.
  label: string
  closeLabel: string
  onClose: () => void
  children: ReactNode
}) {
  useEffect(() => {
    if (!open) return
    const closeOnEscape = (event: KeyboardEvent) => {
      // A dialog opened from inside the sheet has already taken this Escape.
      if (event.key === "Escape" && !event.defaultPrevented) onClose()
    }
    document.addEventListener("keydown", closeOnEscape)
    return () => document.removeEventListener("keydown", closeOnEscape)
  }, [open, onClose])

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={label}
      aria-hidden={!open || undefined}
      inert={!open || undefined}
      className={cn(
        "fixed inset-0 z-40 flex flex-col bg-background transition-transform duration-200 ease-out motion-reduce:transition-none",
        !open && (side === "start" ? "-translate-x-full" : "translate-x-full")
      )}
    >
      <div className="flex shrink-0 items-center border-b px-2 py-1">
        <Button
          type="button"
          variant="ghost"
          size="icon-lg"
          aria-label={closeLabel}
          onClick={onClose}
        >
          <XIcon />
        </Button>
      </div>
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        {children}
      </div>
    </div>
  )
}
