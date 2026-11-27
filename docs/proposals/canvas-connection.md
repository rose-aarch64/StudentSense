---
status: in-progress
code:
  - surfsense_local/backend/modules/egress
  - surfsense_local/backend/shared/secrets.py
  - surfsense_local/backend/modules/folders/router.py
  - surfsense_local/backend/modules/documents/router.py
---

# Canvas connection

> Connect a school's Canvas LMS once, and each active course becomes a workspace: its syllabus, assignments, announcements and modules as notes, its pages and files in one folder per Canvas module, and its assignments in the [to-do list](todo-list.md). Reading only. Nothing is written to Canvas.

A prototype ran outside SurfSense against a real Canvas and SurfSense's own API. It works, and it showed what a built-in version must do differently.

## What changes

| | Today | With this |
|---|---|---|
| Class material | uploaded by hand | synced from Canvas, one workspace per course |
| Structure | the user's folders | one folder per Canvas module, in course order |
| Assignments | read in Canvas | tasks with due dates in the to-do list |
| A change in Canvas | not seen | the next sync updates, moves or renames what changed |

## What the prototype found

- **The Pages tab can be off and the pages still readable.** The page list answers `404 That page has been disabled for this course`. The same pages are readable by slug through the module items. All three of the author's courses were like this.
- **A file link is signed and may sit on another host.** The Canvas token must not travel there, so the download uses a client of its own.
- **SurfSense keeps an upload's last path segment as its title** (`title_of` in `documents/storage.py`). Canvas names a file `A/B.pptx`, SurfSense stores `B.pptx`, and matching by Canvas's name made a duplicate.
- **Matching by name breaks when Canvas changes.** A renamed or inserted module renames every later folder, and a retitled page leaves its old note behind. Everything must be matched by Canvas's ids.

## Decisions

- **Identity is Canvas's ids.** A `canvas_links` table maps `(kind, canvas_id)` to the local workspace, folder, document or task, where `kind` is course, module, page, file or assignment. A renamed module renames its folder, a page retitled in Canvas updates its note, and a file whose module changed is moved. Nothing is matched by name once linked; a link made before the table existed falls back to name matching once.
- **Folders are numbered and named after the module**, such as `02 · Module B Cybersecurity Threats`, with a teacher's leading date range dropped. Items in no module go to `Unsorted`.
- **The token is encrypted like a connection's key** ([`shared/secrets.py`](../../surfsense_local/backend/shared/secrets.py), [connections](../architecture/connections.md#where-keys-live)) and never returned by a route or written to a log.
- **Egress is asked per host** ([egress](../architecture/egress.md)). The school's Canvas host is one destination. A file's signed link names another host at download time, and `egress.require()` checks it before the connection opens.
- **Reading only.** The client issues `GET` requests. A token needs no more than a student's own access.
- **Gone from Canvas is listed, never deleted.** A linked item Canvas no longer returns is shown in the sync result, and the user decides.
- **Files take the existing upload route**, so its per-folder dedup and its supported types apply. A type SurfSense cannot read is skipped before it is downloaded.
- **The prototype's MCP server stays outside.** It answers live questions from the agent as a [plugin](../architecture/plugins.md); the sync does not need it.

## Not decided here

- Whether a sync runs as a background job on the existing queues ([ADR 0008](../adr/0008-two-job-queues.md)) or inside a request. The prototype ran in one request and took a few minutes for about 430 MB.
- A schedule. The first version syncs on the user's action.
- More than one Canvas connection, for a user at two schools.
- Discussions, quizzes and grades. The prototype read none of them.
- A reused id. SQLite hands a deleted row's id to the next one made. If the user deletes a synced workspace, makes a different one, and that one takes the id before the next sync, the stale link names the new workspace. A link could also keep the local row's creation time, though that has only second precision, so it narrows the gap and does not close it.

## Checks

- **Tests, first:** a module inserted before the others, a module renamed, a page retitled, an item removed from Canvas, a file whose name contains a slash, a course whose Pages tab is off, and a Canvas token that never appears on a request to another host.
- **Manual:** a real Canvas with a course that has modules, files and a disabled Pages tab.
- **Docs:** `docs/architecture/canvas.md` is added when this ships.
