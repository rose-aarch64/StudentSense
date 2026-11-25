import type { ReactNode } from "react"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"
import { cn } from "@/lib/utils"

import type { Workspace } from "./api"
import { workspaceIcon } from "./workspace-icons"

function workspaceMark(name: string) {
  return (
    name
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((word) => word[0])
      .join("")
      .toUpperCase() || "W"
  )
}

/** One workspace in the rail: its icon, or its initials, then its name. */
export function WorkspaceRow({
  workspace,
  selected,
  nested,
  onSelect,
  menu,
}: {
  workspace: Workspace
  selected: boolean
  // Under a folder's header, so inset.
  nested: boolean
  onSelect: () => void
  // The items of its context menu.
  menu: ReactNode
}) {
  const Icon = workspaceIcon(workspace.icon ?? null)
  return (
    <ContextMenu>
      <ContextMenuTrigger
        render={
          <div className={cn("flex w-full", nested && "pl-3")}>
            <Button
              variant="ghost"
              className={cn(
                "h-9 w-full justify-start gap-2.5 rounded-xl px-2 font-normal",
                selected &&
                  "bg-sidebar-accent font-medium text-sidebar-accent-foreground"
              )}
              // The initials beside the name would otherwise join its accessible name.
              aria-label={workspace.name}
              aria-current={selected ? "page" : undefined}
              onClick={onSelect}
            >
              {Icon ? (
                <span className="flex size-7 shrink-0 items-center justify-center">
                  {/* workspaceIcon returns a fixed registry's components, never a new one. */}
                  {/* eslint-disable-next-line react-hooks/static-components */}
                  <Icon className="size-[18px]" />
                </span>
              ) : (
                <Avatar className="size-7 rounded-lg">
                  <AvatarFallback className="rounded-lg text-[10px] font-semibold">
                    {workspaceMark(workspace.name)}
                  </AvatarFallback>
                </Avatar>
              )}
              <span className="min-w-0 flex-1 truncate text-left">
                {workspace.name}
              </span>
            </Button>
          </div>
        }
      />
      <ContextMenuContent className="w-44" finalFocus={false}>
        {menu}
      </ContextMenuContent>
    </ContextMenu>
  )
}
