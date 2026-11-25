import { Skeleton } from "@/components/ui/skeleton"
import { SettingsSection } from "@/features/settings/settings-section"
import { intl } from "@/i18n/intl"

import { ConnectedPanel } from "./connected-panel"
import { ConnectForm } from "./connect-form"
import { useConnection } from "./use-canvas"

/** Settings › Canvas: bring a school's classes in, and keep them current. */
export function CanvasSettings() {
  const connection = useConnection().data

  return (
    <SettingsSection
      title={intl.formatMessage({
        id: "canvas_settings_title",
        defaultMessage: "Canvas",
      })}
      description={intl.formatMessage({
        id: "canvas_settings_body",
        defaultMessage:
          "Bring your classes in from Canvas: a workspace per class, with its pages, files and assignments. SurfSense only reads Canvas.",
      })}
    >
      {connection === undefined ? (
        <Skeleton className="h-24 w-full" />
      ) : connection.connected ? (
        <ConnectedPanel status={connection} />
      ) : (
        <ConnectForm />
      )}
    </SettingsSection>
  )
}
