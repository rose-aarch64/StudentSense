import { useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { intl } from "@/i18n/intl"
import { cn } from "@/lib/utils"

import { WORKSPACE_ICON_KEYS, workspaceIcon } from "./workspace-icons"

/** A grid of icons for one workspace. None goes back to its initials. */
export function WorkspaceIconDialog({
  open,
  workspaceName,
  currentKey,
  onOpenChange,
  onOpenChangeComplete,
  onSave,
}: {
  open: boolean
  workspaceName: string
  currentKey: string | null
  onOpenChange: (open: boolean) => void
  onOpenChangeComplete: (open: boolean) => void
  onSave: (key: string | null) => Promise<boolean>
}) {
  const [choice, setChoice] = useState(currentKey)

  const save = async (key: string | null) => {
    if (await onSave(key)) onOpenChange(false)
  }

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      onOpenChangeComplete={onOpenChangeComplete}
    >
      <DialogContent className="select-none sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>
            {intl.formatMessage(
              {
                id: "workspaces_icon_dialog_title",
                defaultMessage: "Icon for {name}",
              },
              { name: workspaceName }
            )}
          </DialogTitle>
          <DialogDescription>
            {intl.formatMessage({
              id: "workspaces_icon_dialog_body",
              defaultMessage: "Pick one. None goes back to the initials.",
            })}
          </DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-6 gap-1.5">
          {WORKSPACE_ICON_KEYS.map((key) => {
            const Icon = workspaceIcon(key)
            return (
              <Button
                key={key}
                type="button"
                variant="ghost"
                size="icon-lg"
                title={key}
                aria-label={key}
                aria-pressed={choice === key}
                className={cn(
                  "rounded-lg",
                  choice === key && "bg-sidebar-accent ring-2 ring-primary"
                )}
                onClick={() => setChoice(key)}
              >
                {Icon ? <Icon className="size-5" /> : null}
              </Button>
            )
          })}
        </div>
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => void save(null)}
          >
            {intl.formatMessage({
              id: "workspaces_icon_dialog_none_button",
              defaultMessage: "None",
            })}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            {intl.formatMessage({
              id: "workspaces_name_dialog_cancel_button",
              defaultMessage: "Cancel",
            })}
          </Button>
          <Button type="button" onClick={() => void save(choice)}>
            {intl.formatMessage({
              id: "workspaces_icon_dialog_save_button",
              defaultMessage: "Save",
            })}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
