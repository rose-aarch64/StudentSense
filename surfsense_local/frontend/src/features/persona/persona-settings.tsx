import { Skeleton } from "@/components/ui/skeleton"
import { SettingsSection } from "@/features/settings/settings-section"
import { intl } from "@/i18n/intl"

import { PersonaEditor } from "./persona-editor"
import { usePersona, useSavePersona } from "./use-persona"

/** Settings › Persona: a note on how the models should talk, like a CLAUDE.md. */
export function PersonaSettings() {
  const saved = usePersona().data
  const save = useSavePersona()

  return (
    <SettingsSection title={label()} description={body()}>
      {saved === undefined ? (
        <Skeleton className="h-40 w-full" />
      ) : (
        <PersonaEditor label={label()} saved={saved.text} save={save} />
      )}
    </SettingsSection>
  )
}

function label() {
  return intl.formatMessage({
    id: "settings_nav_persona_label",
    defaultMessage: "Persona",
  })
}

function body() {
  return intl.formatMessage({
    id: "persona_settings_body",
    defaultMessage:
      "A note on how the models should talk to you, like a CLAUDE.md. It sets tone only, and applies to chat and the Today window.",
  })
}
