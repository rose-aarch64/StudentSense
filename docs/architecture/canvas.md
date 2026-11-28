# Canvas

Connect a school's Canvas LMS once, and each active course becomes a workspace: its syllabus, assignments, announcements and modules as notes, its pages and files in one folder per Canvas module, and its assignments in the [to-do list](todos.md). SurfSense only reads Canvas. Everything it makes is found again by Canvas's own ids, so renaming, reordering or editing in Canvas updates what is here and never duplicates it. Settings › Canvas is the screen, and the routes are `/canvas`.

**Code:** [`surfsense_local/backend/modules/canvas/`](../../surfsense_local/backend/modules/canvas/), [`alembic/versions/0038_canvas_connection.py`](../../surfsense_local/backend/alembic/versions/0038_canvas_connection.py), [`0039_canvas_links.py`](../../surfsense_local/backend/alembic/versions/0039_canvas_links.py) and [`0041_canvas_auto_refresh.py`](../../surfsense_local/backend/alembic/versions/0041_canvas_auto_refresh.py), [`modules/canvas/refresh/`](../../surfsense_local/backend/modules/canvas/refresh/), [`modules/canvas/runlog/`](../../surfsense_local/backend/modules/canvas/runlog/), [`surfsense_local/frontend/src/features/canvas/`](../../surfsense_local/frontend/src/features/canvas/)
**Also:** [egress](egress.md), [connections](connections.md#where-keys-live), [to-do list](todos.md)

## The connection

One row, `canvas_connection` ([data model](data-model.md#canvas_connection)): the school's origin and the access token, encrypted with the install's secret as a provider's key is, and the name Canvas gave the token's owner. No route returns the token.

| Route | Does |
|---|---|
| `GET /canvas/connection` | `connected`, `base_url`, `user_name`, and the refresh's `auto_refresh`, `refreshed_at` and `refresh_error` ([below](#keeping-the-to-do-list-current)) |
| `PATCH /canvas/connection` | takes `{auto_refresh}` and nothing else (`422` otherwise), and is `409 canvas_not_connected` with no connection |
| `PUT /canvas/connection` | takes `base_url` and `token`, asks Canvas who the token belongs to (`/users/self`), and keeps both, leaving `auto_refresh` as it was and clearing `refresh_error`, since a new token may be the fix for a refused one. A refusal is `422 canvas_token_refused`, an address that is not plain https off this computer is `422 canvas_needs_https`, and an unreachable Canvas is `502 canvas_unreachable` |
| `DELETE /canvas/connection` | forgets the token, and is `204` whether or not there was one |
| `GET /canvas/log` | the last Sync or Check's log, from `after`, for the screen to poll ([The run log](#the-run-log)) |
| `GET /canvas/workspaces/{id}/course` | a synced class's modules in Canvas's order, each item tied to the source it became, for the [Modules view](#the-modules-view). `synced: false` for a workspace Canvas did not make, and for a class not synced since the outline was kept, which also answers `needs_sync: true` |

An address is read as the user typed or pasted it: a bare host is https, and a path after the host is dropped. Plain http is allowed only on this computer, where the token never crosses a network ([`address.py`](../../surfsense_local/backend/modules/canvas/address.py)).

## Egress

The school's host is its own destination, asked about with the purpose `canvas` before anything is sent, when connecting, and again at every sync and every background refresh pass. A course's files are fetched from signed links that may sit on other hosts, so a sync asks about every distinct host in one question before it writes or fetches anything for that course ([`consent.py`](../../surfsense_local/backend/modules/canvas/consent.py)). A refused host is recorded off, so Settings › Network lists it to allow.

## The sync

`POST /canvas/sync`, with an optional `term` to name one ([`sync/run.py`](../../surfsense_local/backend/modules/canvas/sync/run.py)). With none named, it syncs the current term only ([`sync/term.py`](../../surfsense_local/backend/modules/canvas/sync/term.py)): a course whose term's dates cover today. A course in a term with no dates, such as an orientation course in "Default Term", is left out. A school whose terms have no dates at all gets every course, and between terms nothing syncs. It refuses with `409 embedding_not_chosen` before a model is chosen, `409 canvas_not_connected` with no connection, and `409 canvas_token_refused` when Canvas no longer accepts the saved token (not `401`, which the app reads as its own sign-in lapsing).

Canvas is read, and files are fetched, with no database session open, because a long read must not hold SQLite's write lock, which every other request waits on. Per course:

1. **Read** the course ([`snapshot.py`](../../surfsense_local/backend/modules/canvas/sync/snapshot.py)): syllabus, assignments with the student's submission, announcements, modules with their items, every page and every file a module holds, and every file the course's text links to or an announcement attaches ([`linked_files.py`](../../surfsense_local/backend/modules/canvas/sync/linked_files.py)). A link counts when it names `/courses/{this course}/files/{id}` on the school's host, as a page, a preview or a download, with or without a query. A linked file Canvas refuses or whose type SurfSense cannot store is skipped, and the run log says so with `file_skipped`. A relative Canvas path in synced text is made the school's address ([`html_text.py`](../../surfsense_local/backend/modules/canvas/html_text.py)). A course may turn its Pages tab off, which Canvas answers with `404`; its pages stay readable through the modules that hold them.
2. **Ask** egress about the hosts its files' links name.
3. **Write**, in one transaction: the workspace, its folders, the notes, the tasks, and any file already held filed in its module's folder. A file not yet held is left for the next step.
4. **Queue** each note whose text is new or changed to be read, after the commit, since the worker is another process.
5. **Fetch** each file not yet held, through a client that never sends the Canvas token, and keep it in a transaction of its own, the way an upload is kept ([`files.py`](../../surfsense_local/backend/modules/canvas/sync/files.py)). One file that cannot be fetched does not stop the rest.

A client that follows `Link` headers pages every list; one that points at another host is never followed, so the token cannot be sent elsewhere ([`client.py`](../../surfsense_local/backend/modules/canvas/client.py)).

## What is made, and found again

`canvas_links` ([data model](data-model.md#canvas_links)) maps a Canvas id to the local row it became. `kind` is plain text, so a new kind needs no table rebuild.

| Kind | Canvas id | Local item |
|---|---|---|
| `course` | the course | the workspace, named for the course and renamed with it |
| `term` | the term | a [workspace folder](workspace-folders.md#canvas-sync), named for the term and renamed with it, that holds the term's workspaces |
| `overview_folder`, `unsorted_folder` | the course | the `Overview` folder of summary notes, and `Unsorted` for a page or assignment in no module |
| `module` | the module | its folder, such as `02 · Module B Threats`: numbered by position, the teacher's leading dates dropped, renamed as the module is |
| `syllabus_note`, `assignments_note`, `announcements_note`, `modules_note`, `links_note` | the course | a summary note titled `Canvas · Syllabus` and so on, left out when empty. `Canvas · Links` lists each module's external links with their addresses, as a markdown link each, since the Modules note names a link but cannot be followed from |
| `page` | the page | a note titled `Canvas · Page · <title>`, filed in its module's folder, retitled and moved as the page is |
| `file` | the file | a document titled as an upload is (its last path segment), moved with its module, with the file's size and modified time kept to tell an edit. A file only the text links to, or an announcement attaches, is filed in the `Canvas files` folder instead; a file a module also holds stays in its module |
| `attachments_folder` | the course | the `Canvas files` folder at the top of the class's Library, made only when a class has such a file, and never renamed back after the student renames it |
| `assignment` | the assignment | a [task](todos.md) |
| `assignment_note` | the assignment (a graded quiz or discussion is the assignment too) | a note titled `Canvas · Assignment · <name>` with its due date, points and description, filed in the folder of the first module holding it, or in `Unsorted` for an assignment in no module, and retitled as the assignment is |
| `textbook_folder` | the course | the `Textbook` folder at the top of the class's Library, made once, never written into by a sync, and left as the student renames it |

What the user made earlier is adopted once instead of remade: a workspace named exactly for the course, a top-level folder with a module's name, a note with the same title, and a file with the same title in one of the course's folders. A link to something the user deleted is made good again, except a task, which stays deleted. Nothing is ever deleted because Canvas dropped it.

Canvas keeps rich text as HTML. A note keeps its words, each link as a markdown link and each picture as a markdown image; a picture inlined as `data:` keeps only its description ([`html_text.py`](../../surfsense_local/backend/modules/canvas/html_text.py)).

## The Modules view

A synced class can be shown the way Canvas shows its Modules page. No migration backs it, so a rollback to an older image needs no database restore.

- **What is saved.** Each sync keeps the course's modules in the `Canvas · Modules` note's `document_metadata`, under `canvas_modules` ([`sync/outline.py`](../../surfsense_local/backend/modules/canvas/sync/outline.py)): per module its items in Canvas's order, headers and links included, each with its type, title, Canvas id (page, file or assignment), link address, due date and points. Items carry Canvas ids, not local ones, so a file not yet fetched costs nothing. The note's edit route changes only its title and text, so a user's edit leaves the outline alone, and a change to the outline alone queues no re-read of the note. A course left with no modules makes no Modules note, so the sync empties the kept note's outline instead.
- **What is read.** `GET /canvas/workspaces/{id}/course` ([`course_view/`](../../surfsense_local/backend/modules/canvas/course_view/)) resolves the outline against `canvas_links` and the workspace, and returns for each item the document it became, if one exists here, and for each module its folder, if the module held any source. It also returns the Textbook folder, the ids of the Syllabus, Announcements, Assignments and Links notes, and `files`, a map from each Canvas file id the workspace holds, module files and linked files alike, to the document it became.
- **Links to Canvas files.** A note keeps the Canvas link. In a note reader (the Canvas tabs and the source preview), a link whose file id is in `files` opens that source in the preview window instead of leaving for Canvas ([`canvas-file-links.tsx`](../../surfsense_local/frontend/src/features/sources/course-view/canvas-file-links.tsx), [`canvas-aware-link.tsx`](../../surfsense_local/frontend/src/features/chat/canvas-aware-link.tsx)). Any other link is the reader's own link, with its safety check.
- **What is shown.** For a class with `synced: true` or `needs_sync: true`, the Sources panel shows a Files / Canvas switch ([`features/sources/course-view/`](../../surfsense_local/frontend/src/features/sources/course-view/)). Files is the tree as always. Canvas is a row of tabs (Modules, Syllabus, Announcements and Assignments when those notes exist, Textbook, Links), each shown in place. Modules is one block per module; Syllabus, Announcements, Assignments and Links read the class's Overview note of that name, and Textbook is described below. A module header and each page, file or assignment carry the tick boxes the tree has, through the same selection, so the chat reads ticks made in either view. A module header also counts the rows it shows that are filed in another module's folder, and ticks them with its folder. A link opens in a new tab and has no box. A header with no folder has no box. On a phone it opens from the same sources bar as the tree.
- **The Textbook.** The chip shows the books in the class's `Textbook` folder and an **Import textbook** button, which uploads PDF, EPUB, MOBI or AZW3 files into that folder. Nothing is guessed from Canvas, which sends no book text.

## Tasks

An assignment becomes a task with its name and due date, in the course's workspace. A submission Canvas has received (`submitted`, `graded` or `pending_review`) marks it done. The sync never clears a check. A task the user deleted is not made again, unless its workspace was made fresh, since its tasks went with it ([`tasks.py`](../../surfsense_local/backend/modules/canvas/sync/tasks.py)).

## Keeping the to-do list current

A student who is away for days wants the to-do list right on return, and a full sync reads every class's pages and files, which is too much to run unattended. So there is a lighter pass, off until the user turns it on in Settings › Canvas (`auto_refresh`, from `0041`).

- **When.** [`refresh/schedule.py`](../../surfsense_local/backend/modules/canvas/refresh/schedule.py) runs a pass 1 minute after the API starts, then every 6 hours, for as long as the API runs: the whole day in Docker, only while the app is open on the desktop. It is its own entry in the lifespan, not one of the licence loops, which do nothing while licensing is off ([ADR 0092](../adr/0092-surfsense-is-free-and-licensing-is-off.md)). Each pass reads the setting first, so switching it off, or disconnecting, takes effect at the next pass with no Canvas request made. A failed pass waits for the next and is never retried at once.
- **What a pass reads.** [`refresh/run.py`](../../surfsense_local/backend/modules/canvas/refresh/run.py) lists the active courses, keeps the current term's as a sync does, skips any with no workspace yet (a new class needs one Sync now), and reads each remaining class's assignments with the student's submission. Canvas is read with no database session open. It makes no workspace, folder, note or file and fetches nothing, so the only host it asks is the school's, checked against Settings › Network at every pass.
- **What it writes.** `sync_tasks`, unchanged, one short transaction per class, so the rules of [Tasks](#tasks) hold: a due date follows Canvas, a handed-in assignment is marked done, a check is never cleared, and a deleted task stays deleted. A class Canvas no longer finds is skipped and the rest still refresh. A class whose write loses a race with a manual sync is skipped until the next pass.
- **How it is reported.** The pass records `refreshed_at` on success and `refresh_error` on a failure, as one of `canvas_token_unreadable`, `canvas_token_refused`, `canvas_unreachable` or `egress_disabled`, and changes no task. Settings shows the time or the reason under the switch.

## Stale files

A file's size and modified time are kept when it is stored. `GET /canvas/stale`, with an optional `term`, compares them with Canvas and returns, for each synced course, the files `changed` and the files `gone`. It asks Canvas about the files and fetches no bytes, writes nothing and queues nothing. A sync replaces an edited file's stored copy in place, keeping its document, and queues it to be read again; a re-upload that fails validation, or repeats bytes already held in the folder, leaves the old copy. A file Canvas no longer lists is reported and left.

## The run log

Sync and Check answer once, at the end. While one runs, [`modules/canvas/runlog/`](../../surfsense_local/backend/modules/canvas/runlog/) keeps a log of what it reads and fails on, which `GET /canvas/log?run=<id>&after=<n>` serves: `{run, kind, state, entries, next}`, with `state` `idle` before any run, then `running`, `done` or `failed`. It returns the entries after `n` of that run, or the whole current log when `run` is not the current one, which is how a page that outlived a run starts over.

- **One log, in memory.** The last run only, whichever kind: starting a Sync or Check replaces it, and the older run's handle drops any write it still makes, so lines never mix. It holds at most 1000 entries and keeps numbering past that, dropping the oldest, and is lost when the API restarts. It is never written to disk.
- **Entries.** `{n, level, code, params}`: a code and plain parameters, which the app words itself so the log is translated like the rest of the screen. A sync writes `sync_started`, then per class `class_started{name}`, `class_read{name, assignments, announcements, modules, pages, files}`, `pages_tab_off{name}` when the Pages tab was off, and per file `file_kept`, `file_updated`, `file_skipped` (refused, or the same bytes already held, which is not an error) or `file_failed` (the download failed, at level `error`), each with `{name}`; last `finished{classes, errors}`. A file already held and current writes nothing. A Check writes `check_started`, `class_checked{name, changed, gone}` per class it compared, and `finished`. A run that raises writes `stopped{error}` at level `error`, with the code the routes answer with, and the lines before it stay.
- **What it never holds.** No token, no signed file link, no address: class and file names and counts only.
- **Writing never breaks a run.** A line that cannot be written is dropped; a sync never fails for its log ([`log.py`](../../surfsense_local/backend/modules/canvas/runlog/log.py), [`logged_run.py`](../../surfsense_local/backend/modules/canvas/runlog/logged_run.py)).

## The screen

[Settings › Canvas](../../surfsense_local/frontend/src/features/canvas/canvas-settings.tsx) shows a form for the school's address and a token until connected. Connected, it shows whose Canvas it is and three buttons: Sync now, which holds while it runs and then says how many classes it synced and which files it updated or found gone; Check for changes; and Disconnect. A sync also refreshes the to-do list. Under the buttons is the switch, Keep my to-do list up to date, with one line saying when the background pass last worked or why it did not. Below that is the Log box ([`canvas-log-box.tsx`](../../surfsense_local/frontend/src/features/canvas/canvas-log-box.tsx)): it reads the log once on opening, to show the last run or find one still going, and polls it every second while a run goes on, then once more when the run this window started ends. It words each code through [`canvas-log-text.ts`](../../surfsense_local/frontend/src/features/canvas/canvas-log-text.ts), shows `error` lines in the destructive color, and skips a code this release does not know. The consent prompt's wording for `canvas` is in [`egress/api.ts`](../../surfsense_local/frontend/src/features/egress/api.ts).

## Known gaps

- SQLite hands a deleted row's id to the next one made. If the user deletes a synced workspace, makes a different one, and it takes that id before the next sync, the stale link names it. A creation time would narrow this but not close it.
- A sync is one request and can take minutes for many large files; it is not a background job, and nothing shows a percentage, only the lines the [run log](#the-run-log) writes as it goes.
- The run log keeps the last Sync or Check only, and nothing from the background to-do refresh.
- A file adopted from an earlier tool is taken as current, so an edit made before the first sync is not seen.
- The screen offers no choice of term or course, though the routes take `term`. An orientation course already synced stays, with its tasks under "Show N older".
- Nothing tells an open app to refresh, so the workspace list, folders and documents a sync made may need a reload to appear.
- The background pass adds no classes: a new term's first classes need one Sync now, and nothing says so.
- A handed-in assignment the student unchecked is checked again by the next pass, since `sync_tasks` marks an unchecked task done whenever the work is handed in.
- An open to-do dialog shows what a pass found only after it is reopened or refetches.
- Discussions, quizzes and grades are not read, beyond the assignment a graded quiz or discussion is, and one school is connected at a time.
- A linked file of a type SurfSense cannot store (an old `.doc`, for example), or one Canvas refuses, keeps its Canvas link. Check for changes compares module files only, so it neither sees edits to linked files nor reports them gone, and there is no size cap. A note's link opens a held file by its Canvas file id alone, not by school or course.
- A class with no modules has no Modules note, so it has no outline: its Canvas switch asks for a sync that never changes that.
- A class synced before the outline was kept shows a Canvas switch with one line telling the student to run Sync now, and nothing more until they do.
- A graded quiz or discussion is tied to its assignment by the quiz's or topic's id, as Canvas's assignment object names them. That mapping was written from the API's description and has not been run against a school with quizzes.
- Edits to a summary note's text, the Modules note included, are replaced by the next sync that changes Canvas's text.
- A note is adopted by title anywhere in the workspace, so a note in `Textbook` titled as a Canvas note would be adopted and moved out.
