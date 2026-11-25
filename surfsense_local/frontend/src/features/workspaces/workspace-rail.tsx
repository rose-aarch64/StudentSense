import { useState } from "react"
import {
  Image01Icon,
  PencilIcon,
  PlusIcon,
  Settings2Icon,
  Trash2Icon,
} from "@/components/ui/icons"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  ContextMenuGroup,
  ContextMenuItem,
  ContextMenuSeparator,
} from "@/components/ui/context-menu"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useStartupReveal } from "@/features/startup/use-startup-reveal"
import { intl } from "@/i18n/intl"
import { cn } from "@/lib/utils"

import type { Workspace, WorkspaceFolder } from "./api"
import {
  readCollapsedFolders,
  writeCollapsedFolders,
} from "./collapsed-folders"
import { FolderHeader } from "./folder-header"
import { MoveToFolderMenu } from "./move-to-folder-menu"
import { groupWorkspaces } from "./rail-groups"
import { WorkspaceIconDialog } from "./workspace-icon-dialog"
import { WorkspaceNameDialog } from "./workspace-name-dialog"
import { WorkspaceRow } from "./workspace-row"

function folderNameLabel() {
  return intl.formatMessage({
    id: "workspaces_folder_name_aria",
    defaultMessage: "Folder name",
  })
}

export function WorkspaceRail({
  workspaces,
  folders,
  activeWorkspaceId,
  isMutating,
  onSelect,
  onCreate,
  onRename,
  onDelete,
  onOpenSettings,
  onSetIcon,
  onMoveToFolder,
  onCreateFolder,
  onRenameFolder,
  onDeleteFolder,
}: {
  workspaces: Workspace[]
  folders: WorkspaceFolder[]
  activeWorkspaceId: number
  isMutating: boolean
  onSelect: (id: number) => void
  onCreate: (name: string) => Promise<boolean>
  onRename: (id: number, name: string) => Promise<boolean>
  onDelete: (id: number) => Promise<boolean>
  onOpenSettings: () => void
  onSetIcon: (id: number, key: string | null) => Promise<boolean>
  onMoveToFolder: (id: number, folderId: number | null) => Promise<boolean>
  onCreateFolder: (name: string) => Promise<WorkspaceFolder | null>
  onRenameFolder: (id: number, name: string) => Promise<boolean>
  onDeleteFolder: (id: number) => Promise<boolean>
}) {
  // The name dialog, creating ("new") or renaming; cleared once it has closed.
  const [naming, setNaming] = useState<Workspace | "new" | null>(null)
  const [namingOpen, setNamingOpen] = useState(false)
  const [deleting, setDeleting] = useState<Workspace | null>(null)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [iconFor, setIconFor] = useState<Workspace | null>(null)
  const [iconOpen, setIconOpen] = useState(false)
  // The folder name dialog: a new folder, filed with a workspace when it was made
  // from that workspace's menu, or a folder's rename.
  const [foldering, setFoldering] = useState<
    | { kind: "create"; workspace: Workspace | null }
    | { kind: "rename"; folder: WorkspaceFolder }
    | null
  >(null)
  const [folderingOpen, setFolderingOpen] = useState(false)
  const [deletingFolder, setDeletingFolder] = useState<WorkspaceFolder | null>(
    null
  )
  const [deleteFolderOpen, setDeleteFolderOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(readCollapsedFolders)
  const reveal = useStartupReveal()
  const { unfiled, groups } = groupWorkspaces(workspaces, folders)

  const openNaming = (target: Workspace | "new") => {
    setNaming(target)
    setNamingOpen(true)
  }

  const toggleFolder = (id: number) => {
    const next = new Set(collapsed)
    if (!next.delete(id)) next.add(id)
    setCollapsed(next)
    writeCollapsedFolders(next)
  }

  const row = (workspace: Workspace, nested: boolean) => (
    <WorkspaceRow
      key={workspace.id}
      workspace={workspace}
      selected={workspace.id === activeWorkspaceId}
      nested={nested}
      onSelect={() => onSelect(workspace.id)}
      menu={
        <ContextMenuGroup>
          <ContextMenuItem onClick={() => openNaming(workspace)}>
            <PencilIcon />
            {intl.formatMessage({
              id: "workspaces_rail_rename_label",
              defaultMessage: "Rename",
            })}
          </ContextMenuItem>
          <ContextMenuItem
            onClick={() => {
              setIconFor(workspace)
              setIconOpen(true)
            }}
          >
            <Image01Icon />
            {intl.formatMessage({
              id: "workspaces_rail_icon_label",
              defaultMessage: "Icon…",
            })}
          </ContextMenuItem>
          <MoveToFolderMenu
            folders={folders}
            currentFolderId={workspace.folder_id ?? null}
            onMove={(folderId) => void onMoveToFolder(workspace.id, folderId)}
            onNewFolder={() => {
              setFoldering({ kind: "create", workspace })
              setFolderingOpen(true)
            }}
          />
          <ContextMenuSeparator />
          <ContextMenuItem
            variant="destructive"
            onClick={() => {
              setDeleting(workspace)
              setDeleteOpen(true)
            }}
          >
            <Trash2Icon />
            {intl.formatMessage({
              id: "workspaces_rail_delete_label",
              defaultMessage: "Delete",
            })}
          </ContextMenuItem>
        </ContextMenuGroup>
      }
    />
  )

  const folderMenu = (folder: WorkspaceFolder) => (
    <ContextMenuGroup>
      <ContextMenuItem
        onClick={() => {
          setFoldering({ kind: "rename", folder })
          setFolderingOpen(true)
        }}
      >
        <PencilIcon />
        {intl.formatMessage({
          id: "workspaces_rail_rename_label",
          defaultMessage: "Rename",
        })}
      </ContextMenuItem>
      <ContextMenuItem
        variant="destructive"
        onClick={() => {
          setDeletingFolder(folder)
          setDeleteFolderOpen(true)
        }}
      >
        <Trash2Icon />
        {intl.formatMessage({
          id: "workspaces_rail_delete_label",
          defaultMessage: "Delete",
        })}
      </ContextMenuItem>
    </ContextMenuGroup>
  )

  return (
    <nav
      {...reveal}
      className={cn(
        "flex h-full flex-col bg-app-shell px-2 py-3 text-sidebar-foreground",
        reveal.className
      )}
      aria-label={intl.formatMessage({
        id: "workspaces_rail_aria",
        defaultMessage: "Workspaces",
      })}
    >
      <ScrollArea className="min-h-0 w-full flex-1">
        <div className="flex flex-col gap-1">
          {unfiled.map((workspace) => row(workspace, false))}
          {groups.map(({ folder, workspaces: inside }) => (
            <div key={folder.id} className="mt-1 flex flex-col gap-1">
              <FolderHeader
                folder={folder}
                open={!collapsed.has(folder.id)}
                onToggle={() => toggleFolder(folder.id)}
                menu={folderMenu(folder)}
              />
              {collapsed.has(folder.id)
                ? null
                : inside.map((workspace) => row(workspace, true))}
            </div>
          ))}
          <DropdownMenu>
            <DropdownMenuTrigger
              render={
                <Button
                  variant="ghost"
                  className="mt-1 h-9 w-full justify-start gap-2.5 rounded-xl border border-dashed border-sidebar-border px-2 font-normal text-muted-foreground"
                  disabled={isMutating}
                >
                  <PlusIcon className="mx-1 size-[18px]" />
                  {intl.formatMessage({
                    id: "workspaces_rail_add_label",
                    defaultMessage: "New",
                  })}
                </Button>
              }
            />
            <DropdownMenuContent className="w-44" finalFocus={false}>
              <DropdownMenuGroup>
                <DropdownMenuItem onClick={() => openNaming("new")}>
                  {intl.formatMessage({
                    id: "workspaces_rail_add_workspace_label",
                    defaultMessage: "Workspace",
                  })}
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => {
                    setFoldering({ kind: "create", workspace: null })
                    setFolderingOpen(true)
                  }}
                >
                  {intl.formatMessage({
                    id: "workspaces_rail_add_folder_label",
                    defaultMessage: "Folder",
                  })}
                </DropdownMenuItem>
              </DropdownMenuGroup>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </ScrollArea>

      <Button
        variant="ghost"
        className="h-9 w-full justify-start gap-2.5 rounded-xl px-2 font-normal"
        aria-label={intl.formatMessage({
          id: "workspaces_rail_settings_aria",
          defaultMessage: "Open settings",
        })}
        onClick={onOpenSettings}
      >
        <Settings2Icon className="mx-1 size-[18px]" />
        {intl.formatMessage({
          id: "workspaces_rail_settings_tooltip",
          defaultMessage: "Settings",
        })}
      </Button>

      {naming === "new" ? (
        <WorkspaceNameDialog
          open={namingOpen}
          title={intl.formatMessage({
            id: "workspaces_create_dialog_title",
            defaultMessage: "Create workspace",
          })}
          description={intl.formatMessage({
            id: "workspaces_create_dialog_body",
            defaultMessage: "Keep a separate source library and set of chats.",
          })}
          initialName=""
          submitLabel={intl.formatMessage({
            id: "workspaces_create_dialog_submit_button",
            defaultMessage: "Create",
          })}
          onOpenChange={setNamingOpen}
          onOpenChangeComplete={(open) => {
            if (!open) setNaming(null)
          }}
          onSubmit={onCreate}
        />
      ) : naming ? (
        <WorkspaceNameDialog
          key={naming.id}
          open={namingOpen}
          title={intl.formatMessage({
            id: "workspaces_rename_dialog_title",
            defaultMessage: "Rename workspace",
          })}
          description={intl.formatMessage({
            id: "workspaces_rename_dialog_body",
            defaultMessage:
              "Choose a name that identifies this research context.",
          })}
          initialName={naming.name}
          submitLabel={intl.formatMessage({
            id: "workspaces_rename_dialog_submit_button",
            defaultMessage: "Rename",
          })}
          onOpenChange={setNamingOpen}
          onOpenChangeComplete={(open) => {
            if (!open) setNaming(null)
          }}
          onSubmit={(name) => onRename(naming.id, name)}
        />
      ) : null}
      {iconFor ? (
        <WorkspaceIconDialog
          key={iconFor.id}
          open={iconOpen}
          workspaceName={iconFor.name}
          currentKey={iconFor.icon ?? null}
          onOpenChange={setIconOpen}
          onOpenChangeComplete={(open) => {
            if (!open) setIconFor(null)
          }}
          onSave={(key) => onSetIcon(iconFor.id, key)}
        />
      ) : null}
      {foldering?.kind === "create" ? (
        <WorkspaceNameDialog
          key="folder-create"
          open={folderingOpen}
          title={intl.formatMessage({
            id: "workspaces_folder_create_dialog_title",
            defaultMessage: "New folder",
          })}
          description={intl.formatMessage({
            id: "workspaces_folder_create_dialog_body",
            defaultMessage: "Group workspaces, such as a term’s classes.",
          })}
          initialName=""
          submitLabel={intl.formatMessage({
            id: "workspaces_create_dialog_submit_button",
            defaultMessage: "Create",
          })}
          inputLabel={folderNameLabel()}
          onOpenChange={setFolderingOpen}
          onOpenChangeComplete={(open) => {
            if (!open) setFoldering(null)
          }}
          onSubmit={async (name) => {
            const folder = await onCreateFolder(name)
            if (!folder) return false
            // A folder made from the New menu starts empty.
            if (foldering.workspace) {
              await onMoveToFolder(foldering.workspace.id, folder.id)
            }
            return true
          }}
        />
      ) : foldering?.kind === "rename" ? (
        <WorkspaceNameDialog
          key={foldering.folder.id}
          open={folderingOpen}
          title={intl.formatMessage({
            id: "workspaces_folder_rename_dialog_title",
            defaultMessage: "Rename folder",
          })}
          description={intl.formatMessage({
            id: "workspaces_folder_rename_dialog_body",
            defaultMessage: "Choose a name for this group.",
          })}
          initialName={foldering.folder.name}
          submitLabel={intl.formatMessage({
            id: "workspaces_rename_dialog_submit_button",
            defaultMessage: "Rename",
          })}
          inputLabel={folderNameLabel()}
          onOpenChange={setFolderingOpen}
          onOpenChangeComplete={(open) => {
            if (!open) setFoldering(null)
          }}
          onSubmit={(name) => onRenameFolder(foldering.folder.id, name)}
        />
      ) : null}
      <AlertDialog
        open={deleteFolderOpen}
        onOpenChange={setDeleteFolderOpen}
        onOpenChangeComplete={(open) => {
          if (!open) setDeletingFolder(null)
        }}
      >
        <AlertDialogContent className="select-none">
          <AlertDialogHeader>
            <AlertDialogTitle>
              {intl.formatMessage(
                {
                  id: "workspaces_folder_delete_dialog_title",
                  defaultMessage: "Delete folder {name}?",
                },
                { name: deletingFolder?.name ?? "" }
              )}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {intl.formatMessage({
                id: "workspaces_folder_delete_dialog_body",
                defaultMessage:
                  "Its workspaces are kept and move out of the folder.",
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>
              {intl.formatMessage({
                id: "workspaces_delete_dialog_cancel_button",
                defaultMessage: "Cancel",
              })}
            </AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={() => {
                if (deletingFolder) void onDeleteFolder(deletingFolder.id)
              }}
            >
              {intl.formatMessage({
                id: "workspaces_folder_delete_dialog_confirm_button",
                defaultMessage: "Delete folder",
              })}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <AlertDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        onOpenChangeComplete={(open) => {
          if (!open) setDeleting(null)
        }}
      >
        <AlertDialogContent className="select-none">
          <AlertDialogHeader>
            <AlertDialogTitle>
              {intl.formatMessage(
                {
                  id: "workspaces_delete_dialog_title",
                  defaultMessage: "Delete {name}?",
                },
                {
                  name: deleting?.name ?? "",
                }
              )}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {intl.formatMessage({
                id: "workspaces_delete_dialog_body",
                defaultMessage:
                  "This permanently deletes its chats, documents, and indexed data.",
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>
              {intl.formatMessage({
                id: "workspaces_delete_dialog_cancel_button",
                defaultMessage: "Cancel",
              })}
            </AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={() => {
                if (deleting) void onDelete(deleting.id)
              }}
            >
              {intl.formatMessage({
                id: "workspaces_delete_dialog_confirm_button",
                defaultMessage: "Delete workspace",
              })}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </nav>
  )
}
