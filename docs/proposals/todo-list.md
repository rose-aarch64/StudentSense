---
status: in-progress
code:
  - surfsense_local/backend/alembic/versions
  - surfsense_local/backend/modules/workspaces/models.py
---

# To-do list

> A list of tasks with a due date and a checkbox, across every workspace. A task is written by the user or comes from a source, and the first source is Canvas assignments ([Canvas connection](canvas-connection.md)).

SurfSense holds sources, chats and artifacts, and nothing that says what is still to be done. A student with one workspace per class has no single place to see what is due this week.

## What changes

| | Today | With this |
|---|---|---|
| A thing to do | a note, with no due date and nothing to check off | a task: title, optional due date, done or not |
| What is due this week | read every workspace | one list, filterable by workspace |
| A Canvas assignment | a line in a summary note | a task that appears by itself, with its due date |

## Decisions

- **A task has an optional workspace.** A class's tasks sit in its workspace; a task about nothing in particular has none. Deleting a workspace deletes its tasks, as it deletes its documents ([data model](../architecture/data-model.md#workspaces)).
- **One table, `todos`.** `id`, `workspace_id` (nullable, cascading), `title`, `due_at` (nullable), `done_at` (nullable), `source` (`manual` or `canvas`), `source_key` (nullable, unique together with `source`), `created_at`, `updated_at`. A revision is hand-written, as every schema change is ([ADR 0005](../adr/0005-hand-written-migrations.md)).
- **A source owns what it wrote.** A sync overwrites the title and due date of a task it made and never touches the user's own. The sync may set `done_at` when Canvas reports the assignment submitted, and never clears it, so a task the user checked stays checked.
- **Routes are `/todos`, not nested under a workspace**, since the list spans them: `GET` with optional `workspace_id` and `done` filters, `POST`, `PATCH /{id}` and `DELETE /{id}`.
- **Overdue and due-soon are computed on read**, from `due_at` and the clock, and are not stored.

## Not decided here

- Reminders or notifications.
- Repeating tasks and sub-tasks.
- Whether the agent can read and add tasks as one of its own tools ([agent](../architecture/agent.md#surfsenses-tools)).
- Whether the screen is a sidebar entry or a panel.

## Checks

- **Tests, first:** each route through the public API, the cascade on workspace delete, and a sync that does not clear `done_at`. The migration drift test in `tests/integration/test_migrations.py` covers the table.
- **Docs:** `docs/architecture/todos.md` is added when this ships, with the data model page updated in the same change.
