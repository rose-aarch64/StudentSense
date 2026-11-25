import type { ReactNode } from "react"

import { Button } from "@/components/ui/button"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"
import {
  ChevronDownIcon,
  ChevronRightIcon,
  Folder01Icon,
} from "@/components/ui/icons"

import type { WorkspaceFolder } from "./api"

/** A folder's row: a chevron that opens and closes the workspaces under it. */
export function FolderHeader({
  folder,
  open,
  onToggle,
  menu,
}: {
  folder: WorkspaceFolder
  open: boolean
  onToggle: () => void
  // The items of its context menu; none, no menu.
  menu?: ReactNode
}) {
  const Chevron = open ? ChevronDownIcon : ChevronRightIcon
  const row = (
    <div className="flex w-full">
      <Button
        variant="ghost"
        size="sm"
        className="w-full justify-start gap-1.5 px-2 text-xs font-semibold text-muted-foreground"
        aria-expanded={open}
        onClick={onToggle}
      >
        <Chevron className="size-3.5 shrink-0" />
        <Folder01Icon className="size-3.5 shrink-0" />
        <span className="min-w-0 flex-1 truncate text-left">{folder.name}</span>
      </Button>
    </div>
  )
  if (!menu) return row
  return (
    <ContextMenu>
      <ContextMenuTrigger render={row} />
      <ContextMenuContent className="w-44" finalFocus={false}>
        {menu}
      </ContextMenuContent>
    </ContextMenu>
  )
}
