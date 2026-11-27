import { useId, type ReactNode } from "react"

import { Button } from "@/components/ui/button"
import { ChevronDownIcon } from "@/components/ui/icons"
import { intl } from "@/i18n/intl"
import { cn } from "@/lib/utils"

/**
 * The phone's sources list: a bar under the chat that opens the list over it.
 * The list stays mounted while closed, so its scroll and filter survive.
 */
export function CompactSources({
  open,
  onOpenChange,
  selectedCount,
  children,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  selectedCount: number
  children: ReactNode
}) {
  const listId = useId()
  return (
    <div
      className={cn(
        "flex min-h-0 min-w-0 flex-col border-t bg-background",
        open ? "flex-1" : "shrink-0"
      )}
    >
      <Button
        type="button"
        variant="bare"
        static
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => onOpenChange(!open)}
        className="flex min-h-12 w-full shrink-0 items-center gap-2 px-4 text-left text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-inset"
      >
        <span className="min-w-0 flex-1 truncate">
          {intl.formatMessage(
            {
              id: "dashboard_compact_sources_button",
              defaultMessage: "Sources ({count, number} selected)",
            },
            { count: selectedCount }
          )}
        </span>
        <ChevronDownIcon
          className={cn(
            "size-4 shrink-0 transition-transform duration-150 motion-reduce:transition-none",
            !open && "rotate-180"
          )}
        />
      </Button>
      <div
        id={listId}
        hidden={!open}
        className="flex min-h-0 flex-1 flex-col px-3 pb-2"
      >
        {children}
      </div>
    </div>
  )
}
