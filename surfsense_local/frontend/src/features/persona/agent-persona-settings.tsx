import { Skeleton } from "@/components/ui/skeleton"
import { SettingsSection } from "@/features/settings/settings-section"
import { intl } from "@/i18n/intl"

import { PersonaEditor } from "./persona-editor"
import { useAgentPersona, useSaveAgentPersona } from "./use-persona"

/** Settings › Persona, below the shared note: a shorter one for the agent alone. */
export function AgentPersonaSettings() {
  const saved = useAgentPersona().data
  const save = useSaveAgentPersona()
  const title = intl.formatMessage({
    id: "persona_agent_settings_title",
    defaultMessage: "Agent persona",
  })

  return (
    <SettingsSection
      title={title}
      description={intl.formatMessage({
        id: "persona_agent_settings_body",
        defaultMessage:
          "Used instead of the persona above when the agent answers. Leave it empty to use the persona above. Keep it short: the agent works from long instructions, and small models lose track of the end of a long note.",
      })}
    >
      {saved === undefined ? (
        <Skeleton className="h-40 w-full" />
      ) : (
        <PersonaEditor label={title} saved={saved.text} save={save} />
      )}
    </SettingsSection>
  )
}
