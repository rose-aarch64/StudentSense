import { intl } from "@/i18n/intl"

import type { BoardDay } from "./api"
import { TodoRow } from "./todo-row"

/** This week, one header per day from today through Saturday, empty days too. */
export function WeekSection({ days }: { days: BoardDay[] }) {
  return (
    <section className="flex flex-col gap-2">
      <h3 className="text-xs font-medium text-muted-foreground">
        {intl.formatMessage({
          id: "todos_this_week_title",
          defaultMessage: "This week",
        })}
      </h3>
      {days.map((day) => (
        <div key={day.date} className="flex flex-col gap-1">
          <h4 className="flex items-center gap-2 text-sm font-medium">
            {/* A date alone has no zone, so it is read as the day it names. */}
            {intl.formatDate(new Date(`${day.date}T12:00:00`), {
              weekday: "short",
              month: "short",
              day: "numeric",
            })}
            {day.today ? (
              <span className="rounded-sm bg-primary/10 px-1.5 text-xs text-primary">
                {intl.formatMessage({
                  id: "today_dialog_title",
                  defaultMessage: "Today",
                })}
              </span>
            ) : null}
          </h4>
          {day.todos.length > 0 ? (
            <ul className="flex flex-col gap-1">
              {day.todos.map((todo) => (
                <TodoRow key={todo.id} todo={todo} />
              ))}
            </ul>
          ) : null}
        </div>
      ))}
    </section>
  )
}
