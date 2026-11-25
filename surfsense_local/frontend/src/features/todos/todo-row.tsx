import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Trash2Icon } from "@/components/ui/icons"
import { intl } from "@/i18n/intl"
import { cn } from "@/lib/utils"

import type { Todo } from "./api"
import { useChangeTodo, useDeleteTodo } from "./use-todos"

/** One task: a checkbox named by its title, its due date when it has one, and delete. */
export function TodoRow({ todo }: { todo: Todo }) {
  const change = useChangeTodo()
  const remove = useDeleteTodo()

  return (
    <li className="flex items-center gap-2 text-sm touch:min-h-11 touch:gap-3">
      <Checkbox
        className="touch:size-6"
        checked={todo.done}
        aria-label={todo.title}
        onCheckedChange={(done) =>
          change.mutate({ id: todo.id, change: { done } })
        }
      />
      <span
        className={cn(
          "flex-1 truncate",
          todo.done && "text-muted-foreground line-through"
        )}
      >
        {todo.title}
      </span>
      {todo.due_at ? (
        <span className="shrink-0 text-xs text-muted-foreground">
          {intl.formatDate(new Date(todo.due_at), {
            year: "numeric",
            month: "short",
            day: "numeric",
          })}
        </span>
      ) : null}
      <Button
        type="button"
        variant="ghost"
        size="icon-xs"
        className="shrink-0 text-muted-foreground touch:size-11"
        aria-label={intl.formatMessage(
          { id: "todos_row_delete_aria", defaultMessage: "Delete {title}" },
          { title: todo.title }
        )}
        onClick={() => remove.mutate(todo.id)}
      >
        <Trash2Icon />
      </Button>
    </li>
  )
}
