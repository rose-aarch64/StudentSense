import { Skeleton } from "@/components/ui/skeleton"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { useCompactLayout } from "@/features/dashboard/use-compact-layout"
import { intl } from "@/i18n/intl"
import { cn } from "@/lib/utils"

import { AddTodoForm } from "./add-todo-form"
import { BoardView } from "./board-view"
import { useBoard } from "./use-todos"

/** Every task across the workspaces, in sections by due date. */
export function TodoDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const board = useBoard().data
  const compact = useCompactLayout()

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className={cn(
          "flex flex-col select-none",
          // A card on a desktop; the whole screen on a phone, where a card
          // leaves a strip of chat to mis-tap.
          compact
            ? "h-dvh max-h-dvh w-screen max-w-none rounded-none"
            : "max-h-[min(40rem,calc(100dvh-2rem))] sm:max-w-md"
        )}
      >
        <DialogHeader>
          <DialogTitle>
            {intl.formatMessage({
              id: "todos_dialog_title",
              defaultMessage: "To-do",
            })}
          </DialogTitle>
          <DialogDescription className="text-pretty">
            {intl.formatMessage({
              id: "todos_dialog_body",
              defaultMessage:
                "Tasks across your workspaces, soonest due first.",
            })}
          </DialogDescription>
        </DialogHeader>
        <AddTodoForm />
        {board === undefined ? (
          <Skeleton className="h-24 w-full" />
        ) : (
          <BoardView board={board} />
        )}
      </DialogContent>
    </Dialog>
  )
}
