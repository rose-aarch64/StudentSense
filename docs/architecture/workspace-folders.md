# Workspace folders and icons

Workspaces can be grouped into named folders, and a workspace can carry an icon. The rail that lists them is a labeled column, and a Canvas sync files each course in a folder named for its term.

**Code:** [`modules/workspaces/`](../../surfsense_local/backend/modules/workspaces/), [`modules/canvas/sync/term_folders.py`](../../surfsense_local/backend/modules/canvas/sync/term_folders.py), [`frontend/src/features/workspaces/`](../../surfsense_local/frontend/src/features/workspaces/)

These are folders of workspaces. The folders inside a workspace that hold its sources are a different table ([documents](documents.md#folders)).

## Data

`workspace_folders` and two nullable columns on `workspaces` come from revision `0040` ([data model](data-model.md#workspace_folders)).

- A folder only groups. `workspaces.folder_id` is a foreign key with `ON DELETE SET NULL`, so deleting a folder unfiles its workspaces and never deletes one. Folders do not nest.
- `workspaces.icon` is a slug such as `camera`, or null. The API accepts any lowercase slug of 1 to 32 letters, digits and hyphens. The interface keeps a set of 30 icons from the HugeIcons set the app already uses ([`workspace-icons.ts`](../../surfsense_local/frontend/src/features/workspaces/workspace-icons.ts)) and shows the workspace's initials for a key it does not have, so a later release can add icons without a migration. A key is never removed once released, for the same reason.
- `0040` adds the two columns with `ALTER TABLE ADD COLUMN`, not Alembic's batch mode. The batch rebuilds `workspaces`, and with foreign keys on, SQLite's drop of the old table cascade-deleted every chat thread. The downgrade drops the two columns in place too, which SQLite allows for a column whose `REFERENCES` clause is inline. Tests pin that an upgrade and a downgrade each keep the chats and documents of existing workspaces.
- The inline `REFERENCES` is why the drift check in `tests/integration/test_migrations.py` skips this one foreign key: SQLAlchemy reads a SQLite foreign key's name and `ON DELETE` only from a table-level constraint, so `folder_id` reflects bare. A test reads the rule from SQLite's `pragma_foreign_key_list` instead.

## Routes

| Method | Path | Does |
|---|---|---|
| `GET` | `/workspace-folders` | list, oldest first |
| `POST` | `/workspace-folders` | `{name}`; `201` |
| `PATCH` | `/workspace-folders/{folder_id}` | rename, `{name}` |
| `DELETE` | `/workspace-folders/{folder_id}` | delete the folder and keep its workspaces, unfiled; `204` |
| `PATCH` | `/workspaces/{workspace_id}` | `name`, `icon` and `folder_id`, each optional |

- A folder's name is trimmed and 1 to 200 characters, like a workspace's. An unknown field is `422`, and a folder id in the path that names no folder is `404`.
- A `PATCH` to a workspace changes only the fields it sends. A null `icon` or `folder_id` clears it, a null `name` is `422`, an empty body is `422`, and a `folder_id` that names no folder is `404`.

## The rail

[`workspace-rail.tsx`](../../surfsense_local/frontend/src/features/workspaces/workspace-rail.tsx) is a fixed 216 px column: the dashboard grid and the startup frame both spell that width in full, because Tailwind reads class names, not expressions.

- Workspaces with no folder come first, in the API's order. Then each folder, empty ones too, with its workspaces under a header row. A workspace that names a folder the list lacks counts as unfiled, so a stale id never hides it ([`rail-groups.ts`](../../surfsense_local/frontend/src/features/workspaces/rail-groups.ts)).
- A header's chevron closes and opens its folder. The closed folders are remembered on this device in `localStorage` under `surfsense:collapsed-folders:v1`, and every folder is open until closed ([`collapsed-folders.ts`](../../surfsense_local/frontend/src/features/workspaces/collapsed-folders.ts)).
- The last row is a New menu with Workspace, which opens the create dialog, and Folder, which makes an empty folder. Move to folder › New folder… also makes a folder and files that workspace in it.
- Right-click a workspace for Rename, Icon…, Move to folder and Delete. Move to folder lists the folders with a check on the current one, No folder, and New folder…, which makes the folder and files the workspace in it. Right-click a folder for Rename and Delete. Rows are not dragged.
- The Icon… dialog is a grid. None applies at once and clears the icon; Save applies the choice.
- The bootstrap loads folders beside workspaces and treats a failed folder request as an empty list, so an API without the routes still starts the app. `Workspace.icon` and `.folder_id` are optional on the client type for the same reason.

## Canvas sync

A sync files each course's workspace in a folder for its term ([Canvas](canvas.md#what-is-made-and-found-again)).

- The folder is found by the term's Canvas id in `canvas_links` (kind `term`), else an unlinked folder with the term's exact name is adopted, else a new one is made. Its name follows the term's, so a renamed term renames its folder.
- The folder is resolved for every course, but only a workspace with no folder is filed in it. A workspace the user moved to another folder stays there. One the user unfiled is filed again by the next sync.
- A course with no term, or in a term with no dates such as "Default Term", is left unfiled.
- A folder the user deleted is made again by the next sync that reaches its term, even when every workspace was moved elsewhere.

## Known gaps

- Workspaces and folders cannot be reordered. Both stay oldest first.
- Folders do not nest, and nothing else filters by folder: the to-do list and the Today window still show every workspace.
- The icon set is fixed at 30. There are no emoji and no uploads.
