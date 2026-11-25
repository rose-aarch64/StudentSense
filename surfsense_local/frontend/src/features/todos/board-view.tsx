import { useState } from "react"

import { Button } from "@/components/ui/button"
import { intl } from "@/i18n/intl"

import type { Board } from "./api"
import { BoardSection } from "./board-section"
import { WeekSection } from "./week-section"

function isEmpty(board: Board) {
  const week = board.this_week.reduce((n, day) => n + day.todos.length, 0)
  return (
    week +
      board.overdue.length +
      board.next_week.length +
      board.in_two_weeks.length +
      board.future.length +
      board.undated.length +
      board.done.length ===
    0
  )
}

/** The list in its sections, top to bottom, with what has aged out one click away. */
export function BoardView({ board }: { board: Board }) {
  const [showOlder, setShowOlder] = useState(false)

  return (
    <div className="flex min-h-0 flex-col gap-3 overflow-y-auto">
      {isEmpty(board) ? (
        <p className="text-sm text-muted-foreground">
          {intl.formatMessage({
            id: "todos_list_empty",
            defaultMessage: "Nothing to do",
          })}
        </p>
      ) : null}
      <BoardSection
        title={intl.formatMessage({
          id: "todos_overdue_title",
          defaultMessage: "Overdue",
        })}
        todos={board.overdue}
        collapsible
      />
      {isEmpty(board) ? null : <WeekSection days={board.this_week} />}
      <BoardSection
        title={intl.formatMessage({
          id: "todos_next_week_title",
          defaultMessage: "Next week",
        })}
        todos={board.next_week}
      />
      <BoardSection
        title={intl.formatMessage({
          id: "todos_in_two_weeks_title",
          defaultMessage: "In two weeks",
        })}
        todos={board.in_two_weeks}
      />
      <BoardSection
        title={intl.formatMessage({
          id: "todos_future_title",
          defaultMessage: "Later",
        })}
        todos={board.future}
      />
      <BoardSection
        title={intl.formatMessage({
          id: "todos_undated_title",
          defaultMessage: "No due date",
        })}
        todos={board.undated}
      />
      <BoardSection
        title={intl.formatMessage({
          id: "todos_done_title",
          defaultMessage: "Done",
        })}
        todos={board.done}
        collapsible
        startOpen={false}
      />
      {board.older.length > 0 ? (
        <>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="self-start text-muted-foreground"
            onClick={() => setShowOlder((on) => !on)}
          >
            {showOlder
              ? intl.formatMessage({
                  id: "todos_hide_older_button",
                  defaultMessage: "Hide older",
                })
              : intl.formatMessage(
                  {
                    id: "todos_show_older_button",
                    defaultMessage: "Show {count} older",
                  },
                  { count: board.older.length }
                )}
          </Button>
          {showOlder ? (
            <BoardSection
              title={intl.formatMessage({
                id: "todos_older_title",
                defaultMessage: "Older",
              })}
              todos={board.older}
            />
          ) : null}
        </>
      ) : null}
    </div>
  )
}
