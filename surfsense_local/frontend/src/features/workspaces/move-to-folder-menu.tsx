import {
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuSub,
  ContextMenuSubContent,
  ContextMenuSubTrigger,
} from "@/components/ui/context-menu"
import { CheckIcon, FolderTransferIcon } from "@/components/ui/icons"
import { intl } from "@/i18n/intl"

import type { WorkspaceFolder } from "./api"

/** The "Move to folder" submenu of a workspace's menu. */
export function MoveToFolderMenu({
  folders,
  currentFolderId,
  onMove,
  onNewFolder,
}: {
  folders: WorkspaceFolder[]
  currentFolderId: number | null
  onMove: (folderId: number | null) => void
  onNewFolder: () => void
}) {
  return (
    <ContextMenuSub>
      <ContextMenuSubTrigger>
        <FolderTransferIcon />
        {intl.formatMessage({
          id: "workspaces_rail_move_label",
          defaultMessage: "Move to folder",
        })}
      </ContextMenuSubTrigger>
      <ContextMenuSubContent>
        {folders.map((folder) => (
          <ContextMenuItem key={folder.id} onClick={() => onMove(folder.id)}>
            {folder.id === currentFolderId ? <CheckIcon /> : null}
            {folder.name}
          </ContextMenuItem>
        ))}
        <ContextMenuItem onClick={() => onMove(null)}>
          {currentFolderId === null ? <CheckIcon /> : null}
          {intl.formatMessage({
            id: "workspaces_rail_no_folder_label",
            defaultMessage: "No folder",
          })}
        </ContextMenuItem>
        <ContextMenuSeparator />
        <ContextMenuItem onClick={onNewFolder}>
          {intl.formatMessage({
            id: "workspaces_rail_new_folder_label",
            defaultMessage: "New folder…",
          })}
        </ContextMenuItem>
      </ContextMenuSubContent>
    </ContextMenuSub>
  )
}
