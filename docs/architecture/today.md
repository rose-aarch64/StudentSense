# Today window and persona

A window outside every workspace where the user asks about their day and gets what is due, what is overdue and a suggested order. A persona is a text box in Settings that shapes how the models talk. The window is a row in the sidebar's main nav, above To-do. Its route is `/today`; the persona's are `/persona`.

**Code:** [`surfsense_local/backend/modules/today/`](../../surfsense_local/backend/modules/today/), [`surfsense_local/backend/modules/persona/`](../../surfsense_local/backend/modules/persona/), [`surfsense_local/frontend/src/features/today/`](../../surfsense_local/frontend/src/features/today/), [`surfsense_local/frontend/src/features/persona/`](../../surfsense_local/frontend/src/features/persona/)
**Proposal:** [Today window and persona](../proposals/today-window.md)

## Today

`POST /today/ask` takes the question, the user's local time with its zone, and the conversation so far. It reads every unfinished task with its workspace's name ([`open_tasks.py`](../../surfsense_local/backend/modules/today/open_tasks.py)) and writes the day as text ([`picture.py`](../../surfsense_local/backend/modules/today/picture.py)) in the to-do board's own sections ([the board](todos.md#the-board)): the date, then overdue, due today, later this week, next week, in two weeks, and undated. Later, older and finished tasks are left out. Times are Eastern, the board's zone.

The picture and the persona follow a short instruction in the system message. The selected chat model answers in one reply, not streamed. A `409` says no chat model is selected, or the model is being deleted. The window reads the list and never writes it. The conversation lives in the window and is sent whole with each question, so a closed window forgets.

## Persona

One file, `persona.md` in the data folder, read by `GET /persona` and replaced by `PUT /persona`. An empty text deletes the file. Text over 20,000 characters is refused. [`with_persona`](../../surfsense_local/backend/modules/persona/apply.py) appends it to the instruction of a Basic (Q&A) chat turn, of the Today window and of the agent, after a line saying it sets tone only. The agent's instructions come from `agent_prompt()`, which both engines read: each turn rewrites opencode's configuration from it, so an edit reaches opencode and Claude Code on the next turn ([agent](agent.md#the-configuration)). The edit box is Settings › Persona.

## Known gaps

- The window cannot add, move or finish a task.
- Only tasks are read. Canvas announcements and pages are not.
- The answer arrives whole, with no streaming.
