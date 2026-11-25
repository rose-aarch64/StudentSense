import { useState, type FormEvent } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { intl } from "@/i18n/intl"

import { useAddTodo } from "./use-todos"

/** One line to add a task; Enter adds it too. */
export function AddTodoForm() {
  const [title, setTitle] = useState("")
  const [day, setDay] = useState("")
  const add = useAddTodo()
  const blank = title.trim() === ""

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (blank) return
    add.mutate(
      {
        title: title.trim(),
        // A day has no time: it is due by the end of it, on the user's clock.
        ...(day && { due_at: new Date(`${day}T23:59:00`).toISOString() }),
      },
      {
        onSuccess: () => {
          setTitle("")
          setDay("")
        },
      }
    )
  }

  return (
    <form className="flex gap-2" onSubmit={submit}>
      <Input
        value={title}
        onChange={(event) => setTitle(event.target.value)}
        placeholder={intl.formatMessage({
          id: "todos_add_placeholder",
          defaultMessage: "Add a task",
        })}
        aria-label={intl.formatMessage({
          id: "todos_add_aria",
          defaultMessage: "New task",
        })}
      />
      <Input
        type="date"
        className="w-40 shrink-0"
        value={day}
        onChange={(event) => setDay(event.target.value)}
        aria-label={intl.formatMessage({
          id: "todos_add_due_aria",
          defaultMessage: "Due date",
        })}
      />
      <Button type="submit" disabled={blank || add.isPending}>
        {intl.formatMessage({
          id: "todos_add_button",
          defaultMessage: "Add",
        })}
      </Button>
    </form>
  )
}
