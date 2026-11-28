import { intl } from "@/i18n/intl"

/** What the Modules switch shows for a class synced before its outline was kept. */
export function NeedsSyncLine() {
  return (
    <p className="px-1 py-2 text-sm text-muted-foreground">
      {intl.formatMessage({
        id: "sources_course_needs_sync_empty",
        defaultMessage:
          "Run Sync now in Settings › Canvas to see this class’s modules.",
      })}
    </p>
  )
}
