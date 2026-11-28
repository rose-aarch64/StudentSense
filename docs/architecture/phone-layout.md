# Phone layout

Below a width the desktop layout cannot fit, the dashboard shows one column at a time, with the sidebar and the citation panel as full-screen sheets. A phone can then chat with a workspace's sources and use the to-do list. At and above that width nothing changes.

**Code:** [`features/dashboard/`](../../surfsense_local/frontend/src/features/dashboard/) (`use-compact-layout.ts`, `compact-columns.tsx`, `compact-sheet.tsx`, `compact-header-buttons.tsx`, `use-app-height.ts`, and the compact branch of [`dashboard-page.tsx`](../../surfsense_local/frontend/src/features/dashboard/dashboard-page.tsx)), [`index.css`](../../surfsense_local/frontend/src/index.css), [`index.html`](../../surfsense_local/frontend/index.html)
**Also:** [overview](overview.md), [workspace folders](workspace-folders.md)

## The switch

`COMPACT_BELOW_PX = 1024` in [`use-compact-layout.ts`](../../surfsense_local/frontend/src/features/dashboard/use-compact-layout.ts) is the only place a phone width is named. `useCompactLayout()` reads `matchMedia("(max-width: 1023px)")` through `useSyncExternalStore`, so it is right on the first render and follows a window as it is resized or a device turned. It is `false` where `matchMedia` does not exist, which is every jsdom test that does not stub it.

The desktop grid needs 1328 px (a 216 px rail, a sidebar of at least 272 px, a chat of at least 520 px). 1024 covers phones, rotated phones and a portrait tablet.

## What changes below it

- **The shell.** `DashboardShell` is one column with no minimum width. The workspace rail leaves the grid: `DashboardPage` builds it once and hands it to `WorkspaceDashboard` as `compactRail`.
- **One column.** `WorkspaceDashboard` builds three nodes once, then places them. On a desktop they go in the resizable columns, as always. Compact, an early `return` renders `CompactColumns` instead: the chat fills the window, and no width is measured or dragged.
- **The drawer.** The sidebar, with the rail above it, is a `CompactSheet` that opens from a menu button in the chat's header. It closes on a choice (a chat, New chat, a workspace: choosing a workspace remounts the dashboard), on Escape and from its close button. Its drawer state is never saved, and the desktop's saved sidebar choice is left alone. The drawer no longer holds the sources list: stacked under the rail and the nav it was left about 100 px on an 844 px phone.
- **The sources bar.** [`compact-sources.tsx`](../../surfsense_local/frontend/src/features/dashboard/compact-sources.tsx) is a bar below the chat, "Sources (N selected)", closed on every visit and never saved. Tapping it opens the list over the chat; the chat is then `hidden`, not unmounted, so the thread keeps its scroll and the composer its draft, and the chat's header (the menu and to-do buttons) is out of view until the bar is tapped again. The list is moved out of the drawer, not shown twice. A source preview still lives in the drawer's column, so opening one from the list opens the drawer, and closing the preview (or the drawer) closes both.
- **The detail sheet.** An inspected citation or artifact opens as a second sheet over the chat, with a back button. Studio has no button on a phone.
- **To-do.** A button in the chat's header opens the to-do dialog, which `LeftSidebar` now lets its parent control, so the sidebar's row and the header button open the same one. The dialog fills the screen when compact.
- **A sheet** ([`compact-sheet.tsx`](../../surfsense_local/frontend/src/features/dashboard/compact-sheet.tsx)) keeps its children mounted while closed, so a list keeps its scroll; closed, it is `inert`, `aria-hidden` and off-screen, and it does not slide for reduced-motion users.

## Touch

- A `touch` variant in `index.css` is `@media (hover: none)`. Tailwind's `hover:` and `group-hover:` never apply where nothing hovers, so every control revealed only on hover needs it. Applied to: a message's actions, a thread row's actions in the Chats dialog, a source folder's and document's actions, the reply-thinking chevron and the sources panel's hover text. A class sorter (Prettier's Tailwind plugin) puts custom variants last in a class string.
- **Text size.** The interface runs at 125% (`html { font-size: 125% }`, which every rem size follows). Below the compact width a second rule in `index.css` sets the browser's 100%, so a phone shows sizes 20% smaller than the desktop and `size-11` is a true 44 px. The width is written in the CSS, so `compact-text-size.test.ts` fails if it drifts from `COMPACT_BELOW_PX`.
- On touch, text is 16 px in `Input` and the composer, so iOS does not zoom on focus. The shared `icon-lg` button, the sidebar's rows, the Chats dialog's rows and the to-do rows are 44 px.
- The rail's right-click menus already open on a 500 ms long press on touch, which Base UI's context-menu trigger does; nothing says so.
- `index.html` sets `viewport-fit=cover` and `interactive-widget=resizes-content`, and a `theme-color` for each color scheme. `useAppHeight` sets `--app-height` from `visualViewport` while compact, and the page's height is `var(--app-height, 100svh)`, so a keyboard shrinks the page and the composer stays above it.
- **The composer below 640 px.** A new chat's composer grid has an explicit `minmax(0,1fr)` column, or its content width (about 508 px) stretches the column past a phone. The mode button shows only its icon and chevron (its aria-label keeps the name). The source count hides below 380 px. In a thread the box wraps: the text field takes the full first row, and the add, mic and send buttons sit under it; the disclaimer row wraps too.

## Known gaps

- Studio, source upload and management, Settings, Jobs, Plugins and the Canvas settings screen have no phone design. They are not hidden, and nothing is promised about how they look. A synced class's [Modules view](canvas.md#the-modules-view) is the exception: it lives in the sources list, so it opens from the sources bar.
- A window between 1024 and 1328 px still scrolls sideways, as it always did.
- Crossing the breakpoint moves the chat between parents, so a draft not yet sent is lost; the workspace and the open chat are kept.
- No microphone on a phone: it needs HTTPS, and the Tailscale install is served over plain HTTP.
- jsdom does not evaluate media queries, so the `touch` rules and sizes are checked in a rendered browser, not by the unit tests.
