import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { Switch } from "@/components/ui/switch"
import { intl } from "@/i18n/intl"

import type { ConnectionStatus, StaleCourse, SyncedCourse } from "./api"
import { canvasCodeText, canvasErrorText } from "./canvas-error-text"
import { CanvasLogBox } from "./canvas-log-box"
import {
  useCheck,
  useDisconnect,
  useSetAutoRefresh,
  useSync,
} from "./use-canvas"

/** Connected: who it is, the three things to do, and what the last one found. */
export function ConnectedPanel({ status }: { status: ConnectionStatus }) {
  const sync = useSync()
  const check = useCheck()
  const disconnect = useDisconnect()
  const refresh = useSetAutoRefresh()
  const busy = sync.isPending || check.isPending || disconnect.isPending
  const error = sync.error ?? check.error ?? disconnect.error ?? refresh.error

  return (
    <div className="flex flex-col gap-4">
      <div className="text-sm">
        <p>
          {intl.formatMessage(
            {
              id: "canvas_connected_status",
              defaultMessage: "Connected to {address}",
            },
            { address: status.base_url }
          )}
        </p>
        {status.user_name ? (
          <p className="text-muted-foreground">
            {intl.formatMessage(
              {
                id: "canvas_connected_user_status",
                defaultMessage: "Signed in as {name}",
              },
              { name: status.user_name }
            )}
          </p>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-2">
        <Button type="button" disabled={busy} onClick={() => sync.mutate()}>
          {sync.isPending ? <Spinner data-icon="inline-start" /> : null}
          {intl.formatMessage({
            id: "canvas_sync_button",
            defaultMessage: "Sync now",
          })}
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={busy}
          onClick={() => check.mutate()}
        >
          {check.isPending ? <Spinner data-icon="inline-start" /> : null}
          {intl.formatMessage({
            id: "canvas_check_button",
            defaultMessage: "Check for changes",
          })}
        </Button>
        <Button
          type="button"
          variant="ghost"
          disabled={busy}
          onClick={() => disconnect.mutate()}
        >
          {intl.formatMessage({
            id: "canvas_disconnect_button",
            defaultMessage: "Disconnect",
          })}
        </Button>
      </div>

      <div className="flex items-start gap-3">
        <Switch
          aria-labelledby="canvas-auto-refresh-label"
          checked={status.auto_refresh}
          disabled={busy || refresh.isPending}
          onCheckedChange={(checked) => refresh.mutate(checked)}
        />
        <div className="flex flex-col gap-1 text-sm">
          <p id="canvas-auto-refresh-label" className="font-medium">
            {intl.formatMessage({
              id: "canvas_auto_refresh_label",
              defaultMessage: "Keep my to-do list up to date",
            })}
          </p>
          <p className="text-muted-foreground">
            {intl.formatMessage({
              id: "canvas_auto_refresh_body",
              defaultMessage:
                "Checks Canvas for new assignments, due dates and work you have handed in every few hours while SurfSense is running. It never adds classes.",
            })}
          </p>
          {status.auto_refresh ? <RefreshLine status={status} /> : null}
        </div>
      </div>

      <CanvasLogBox active={sync.isPending || check.isPending} />

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{canvasErrorText(error)}</AlertDescription>
        </Alert>
      ) : null}
      {sync.data ? <SyncSummary courses={sync.data} /> : null}
      {check.data ? <CheckSummary courses={check.data} /> : null}
    </div>
  )
}

/** How the last background pass went: why it failed, when it worked, or that it has not run. */
function RefreshLine({ status }: { status: ConnectionStatus }) {
  const text = status.refresh_error
    ? canvasCodeText(status.refresh_error)
    : status.refreshed_at
      ? intl.formatMessage(
          {
            id: "canvas_auto_refresh_updated_status",
            defaultMessage: "Last updated {when, date, ::yMMMdjm}",
          },
          { when: new Date(status.refreshed_at) }
        )
      : intl.formatMessage({
          id: "canvas_auto_refresh_pending_status",
          defaultMessage: "Not updated yet.",
        })
  return <p className="text-muted-foreground">{text}</p>
}

function files(names: string[]) {
  return intl.formatList(names, { type: "conjunction" })
}

function SyncSummary({ courses }: { courses: SyncedCourse[] }) {
  return (
    <div className="flex flex-col gap-2 text-sm">
      <p>
        {intl.formatMessage(
          {
            id: "canvas_sync_result_status",
            defaultMessage:
              "Synced {count, plural, one {# class} other {# classes}}.",
          },
          { count: courses.length }
        )}
      </p>
      {courses.map((course) => (
        <Changes
          key={course.canvas_id}
          name={course.name}
          refreshed={course.refreshed}
          gone={course.gone}
        />
      ))}
    </div>
  )
}

function CheckSummary({ courses }: { courses: StaleCourse[] }) {
  const stale = courses.filter((c) => c.changed.length || c.gone.length)
  if (stale.length === 0) {
    return (
      <p className="text-sm">
        {intl.formatMessage({
          id: "canvas_check_current_status",
          defaultMessage: "Everything matches Canvas.",
        })}
      </p>
    )
  }
  return (
    <div className="flex flex-col gap-2 text-sm">
      {stale.map((course) => (
        <Changes
          key={course.canvas_id}
          name={course.name}
          changed={course.changed}
          gone={course.gone}
        />
      ))}
    </div>
  )
}

/** One class's lines about its files, none when there is nothing to say. */
function Changes({
  name,
  refreshed = [],
  changed = [],
  gone,
}: {
  name: string
  refreshed?: string[]
  changed?: string[]
  gone: string[]
}) {
  if (!refreshed.length && !changed.length && !gone.length) return null
  return (
    <div>
      <p className="font-medium">{name}</p>
      {refreshed.length ? (
        <p className="text-muted-foreground">
          {intl.formatMessage(
            {
              id: "canvas_refreshed_status",
              defaultMessage: "Updated: {files}",
            },
            { files: files(refreshed) }
          )}
        </p>
      ) : null}
      {changed.length ? (
        <p className="text-muted-foreground">
          {intl.formatMessage(
            {
              id: "canvas_changed_status",
              defaultMessage: "Changed in Canvas: {files}",
            },
            { files: files(changed) }
          )}
        </p>
      ) : null}
      {gone.length ? (
        <p className="text-muted-foreground">
          {intl.formatMessage(
            {
              id: "canvas_gone_status",
              defaultMessage: "No longer in Canvas: {files}",
            },
            { files: files(gone) }
          )}
        </p>
      ) : null}
    </div>
  )
}
