---
status: in-progress
code:
  - surfsense_local/backend/modules/today
  - surfsense_local/backend/modules/persona
  - surfsense_local/frontend/src/features/today
  - surfsense_local/frontend/src/features/persona
---

# Today window and persona

> A window outside every workspace where the user asks "what's going on today?" and gets what is due, what is overdue, and a suggested order for the day. A persona setting, a plain text box like a `CLAUDE.md`, shapes how the app's models talk.

A student with one workspace per class cannot ask one question of all of them. The [to-do list](todo-list.md) already holds every task across workspaces, and Canvas fills it. Nothing reads it back as a plan.

## What changes

| | Today | With this |
|---|---|---|
| "What's going on today?" | open the to-do list and work it out | ask once, get the day |
| Scheduling | by hand | the model suggests an order from the due dates it was given |
| How the models talk | each model's own voice | the user's persona text, added to the instructions of chat and the Today window |

## Decisions

- **The Today window is a chat that reads, never writes.** It answers from a snapshot of the user's tasks and the date. It cannot add, move or finish a task. Write tools with approval prompts are a later step.
- **Not the per-workspace agent.** An agent thread belongs to one workspace's sources, so it cannot see across them. The window calls the selected model directly with the snapshot in its instructions.
- **The snapshot is built on the server at each question**, from `todos` and the workspace names: open tasks that are overdue within two weeks, due in the next fourteen days, or undated. It carries the client's local date and time, since the server does not know the user's time zone.
- **The conversation is kept by the window, not stored.** The client sends the turns so far with each question. A closed window forgets.
- **Persona is one text file, `persona.md`, in the data folder.** Routes `GET` and `PUT /persona`. A missing file reads as empty, and the first run offers the earlier llama-server proxy's text as a starting point the user may save. Rejected: a database table, since one text value gains nothing from a migration.
- **The persona sets tone only.** It is appended to the system instruction after the facts and citation rules, with a line that says so, so it cannot override them.
- **Where the persona applies:** Basic (Q&A) chat, the Today window and agent threads. Both agent engines build their instructions from `agent_prompt()`, so one change covers opencode and Claude Code.

## Not decided here

- Writing to the to-do list from the window.
- Reading Canvas items that are not assignments, such as announcements, into the snapshot.
