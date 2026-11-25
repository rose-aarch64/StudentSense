import { useRef, useState, type SubmitEvent } from "react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { intl } from "@/i18n/intl"

/** A one-line name box for creating or renaming a workspace or a folder. */
export function WorkspaceNameDialog({
  open,
  title,
  description,
  initialName,
  submitLabel,
  inputLabel,
  onOpenChange,
  onOpenChangeComplete,
  onSubmit,
}: {
  open: boolean
  title: string
  description: string
  initialName: string
  submitLabel: string
  // The input's accessible name; a workspace's by default.
  inputLabel?: string
  onOpenChange: (open: boolean) => void
  onOpenChangeComplete: (open: boolean) => void
  onSubmit: (name: string) => Promise<boolean>
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [name, setName] = useState(initialName)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const submit = async (event: SubmitEvent) => {
    event.preventDefault()
    const normalized = name.trim()
    if (!normalized) {
      return
    }
    setIsSubmitting(true)
    if (await onSubmit(normalized)) {
      onOpenChange(false)
    }
    setIsSubmitting(false)
  }

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      onOpenChangeComplete={onOpenChangeComplete}
    >
      <DialogContent
        className="select-none"
        initialFocus={() => {
          inputRef.current?.select()
          return inputRef.current
        }}
      >
        <form onSubmit={(event) => void submit(event)}>
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
            <DialogDescription>{description}</DialogDescription>
          </DialogHeader>
          <Input
            ref={inputRef}
            className="my-4"
            value={name}
            onChange={(event) => setName(event.target.value)}
            aria-label={
              inputLabel ??
              intl.formatMessage({
                id: "workspaces_name_dialog_name_aria",
                defaultMessage: "Workspace name",
              })
            }
            maxLength={200}
          />
          <DialogFooter>
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
            <Button type="submit" disabled={!name.trim() || isSubmitting}>
              {isSubmitting
                ? intl.formatMessage({
                    id: "workspaces_name_dialog_saving_status",
                    defaultMessage: "Saving...",
                  })
                : submitLabel}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
