import { useState, type ReactNode } from "react"

import { intl } from "@/i18n/intl"

import { CompactSheet } from "./compact-sheet"
import { CompactSources } from "./compact-sources"

/**
 * The phone's columns: the chat fills the window, with the sources in a bar
 * below it, and the sidebar and the detail panel are full-screen sheets over
 * it. The workspace rail sits above the sidebar in the drawer, where the
 * desktop has it beside the columns.
 */
export function CompactColumns({
  chat,
  rail,
  sidebar,
  sources,
  selectedSourceCount,
  drawerOpen,
  onDrawerClose,
  detail,
  detailOpen,
  onDetailClose,
}: {
  chat: ReactNode
  rail: ReactNode
  sidebar: ReactNode
  // The sources list, shown in the bar below the chat and not in the sidebar.
  sources: ReactNode
  selectedSourceCount: number
  drawerOpen: boolean
  onDrawerClose: () => void
  // A citation or an artifact, over the chat.
  detail: ReactNode
  detailOpen: boolean
  onDetailClose: () => void
}) {
  // Not saved, like the drawer: a phone opens on the chat.
  const [sourcesOpen, setSourcesOpen] = useState(false)
  return (
    <section className="relative flex h-full min-h-0 min-w-0 flex-col overflow-clip bg-background">
      {/* Hidden, not unmounted, while the list is open: the thread keeps its
          scroll and the composer its draft. */}
      <div
        hidden={sourcesOpen}
        className="flex min-h-0 min-w-0 flex-1 flex-col"
      >
        {chat}
      </div>
      <CompactSources
        open={sourcesOpen}
        onOpenChange={setSourcesOpen}
        selectedCount={selectedSourceCount}
      >
        {sources}
      </CompactSources>
      <CompactSheet
        open={drawerOpen}
        side="start"
        label={intl.formatMessage({
          id: "dashboard_compact_drawer_aria",
          defaultMessage: "Menu",
        })}
        closeLabel={intl.formatMessage({
          id: "dashboard_compact_close_aria",
          defaultMessage: "Close menu",
        })}
        onClose={onDrawerClose}
      >
        {/* The rail takes what it needs, up to 40% of the drawer, then scrolls. */}
        <div className="max-h-[40%] shrink-0 overflow-y-auto border-b">
          {rail}
        </div>
        <div className="flex min-h-0 flex-1 flex-col">{sidebar}</div>
      </CompactSheet>
      <CompactSheet
        open={detailOpen}
        side="end"
        label={intl.formatMessage({
          id: "dashboard_compact_detail_aria",
          defaultMessage: "Details",
        })}
        closeLabel={intl.formatMessage({
          id: "dashboard_compact_back_aria",
          defaultMessage: "Back to the chat",
        })}
        onClose={onDetailClose}
      >
        {detail}
      </CompactSheet>
    </section>
  )
}
