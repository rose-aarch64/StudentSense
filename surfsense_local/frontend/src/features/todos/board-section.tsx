import { useState } from "react"

import { Button } from "@/components/ui/button"
import { ChevronDownIcon, ChevronRightIcon } from "@/components/ui/icons"

import type { Todo } from "./api"
import { TodoRow } from "./todo-row"

/** A titled run of tasks, absent when empty. A collapsible one shows its count. */
export function BoardSection({
  title,
  todos,
  collapsible = false,
  startOpen = true,
}: {
  title: string
  todos: Todo[]
  collapsible?: boolean
  startOpen?: boolean
}) {
  const [open, setOpen] = useState(startOpen)
  if (todos.length === 0) return null

  const rows = (
    <ul className="flex flex-col gap-1">
      {todos.map((todo) => (
        <TodoRow key={todo.id} todo={todo} />
      ))}
    </ul>
  )

  if (!collapsible) {
    return (
      <section className="flex flex-col gap-1">
        <h3 className="text-xs font-medium text-muted-foreground">{title}</h3>
        {rows}
      </section>
    )
  }
  const Chevron = open ? ChevronDownIcon : ChevronRightIcon
  return (
    <section className="flex flex-col gap-1">
      <Button
        type="button"
        variant="ghost"
        size="xs"
        className="self-start px-1 text-xs font-medium text-muted-foreground"
        aria-expanded={open}
        onClick={() => setOpen((on) => !on)}
      >
        <Chevron />
        {title}
        <span>{todos.length}</span>
      </Button>
      {open ? rows : null}
    </section>
  )
}
