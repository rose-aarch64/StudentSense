# To-do list

A list of tasks with a due date and a checkbox, across every workspace. The user writes tasks, and [Canvas](canvas.md) makes one for each assignment. The list is a dialog the sidebar's To-do row opens, and its routes are `/todos`.

**Code:** [`surfsense_local/backend/modules/todos/`](../../surfsense_local/backend/modules/todos/), [`alembic/versions/0037_todos.py`](../../surfsense_local/backend/alembic/versions/0037_todos.py), [`surfsense_local/frontend/src/features/todos/`](../../surfsense_local/frontend/src/features/todos/), [`sidebar-footer.tsx`](../../surfsense_local/frontend/src/features/dashboard/sidebar-footer.tsx)

## The table

`todos`, one row per task ([data model](data-model.md#todos)). A task belongs to a workspace or to none; deleting a workspace deletes its tasks, as it deletes its documents. `source` is `manual` or `canvas`. `source_key` is how a source finds a task it made again, and is unique with `source`; manual tasks have no key and may repeat.

## Routes

| Route | Does |
|---|---|
| `GET /todos` | every task, or those of `workspace_id`, or only open (`done=false`) or done ones. Open tasks come first, soonest due first, then undated ones, then done ones |
| `POST /todos` | adds a task: `title` (1 to 500 characters after trimming), optional `due_at`, optional `workspace_id`. A workspace that does not exist is `404` |
| `PATCH /todos/{id}` | changes only the fields named: `title`, `due_at` (null clears it), `done`. Checking stamps `done_at`; unchecking clears it |
| `DELETE /todos/{id}` | deletes it; a second delete is `404` |
| `GET /todos/board` | every task in its section ([the board](#the-board)) |

A task's `done` is `done_at` being set, computed on read. Overdue and due-soon are not stored.

## The board

Order is derived, never stored: each `GET /todos/board` sorts every task into a section from its dates and the clock, in [`layout.py`](../../surfsense_local/backend/modules/todos/board/layout.py). Today is worked out in one zone, `America/New_York`, since Canvas stores due times in UTC, where 11:59 PM falls on the next day. Weeks run Sunday to Saturday, and this week is today through the coming Saturday. The first rule that matches wins.

| Section | Holds |
|---|---|
| Done | finished, newest first |
| No due date | in the order added |
| Overdue | due before today, oldest first |
| This week | one header per day from today through Saturday, empty days too, today marked |
| Next week, In two weeks | the next two Sunday-to-Saturday weeks, soonest first |
| Later | anything past those |
| Older | not shown: more than 7 days late, or finished over 30 days ago |

Same-day tasks keep the order they were added in. Older tasks are set aside, never deleted: the dialog offers "Show N older". Priority is not a field yet. The Today window reads the same sections ([Today](today.md)).

## Who owns what

A person's tasks are theirs alone. A task [Canvas](canvas.md#tasks) made has its title and due date overwritten by each sync, may be marked done when the assignment is handed in, and never has a check taken away. A task the user deletes stays deleted.

## The screen

The sidebar's To-do row, under Chats, opens a dialog ([`todo-dialog.tsx`](../../surfsense_local/frontend/src/features/todos/todo-dialog.tsx)): a box to add a task with an optional due date, then the board's sections, each row a checkbox named by its title, its due date, and a delete button. Overdue is open and Done is closed, each with a count; empty sections are hidden. A date has no time, so a picked day is due at the end of it on the user's clock. Every change refetches the board, since the server owns its order, so a task just checked moves to Done.

## Known gaps

- The screen lists every task together. It does not filter by workspace or name a task's workspace.
- Nothing pushes changes to an open screen; it refetches after its own changes and when opened.
- No reminders, repeating tasks or sub-tasks, and the agent has no tool to read or add tasks.
