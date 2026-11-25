import { useState } from "react"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"
import { SettingsSection } from "@/features/settings/settings-section"
import { intl } from "@/i18n/intl"

import { usePersona, useSavePersona } from "./use-persona"

/** Settings › Persona: a note on how the models should talk, like a CLAUDE.md. */
export function PersonaSettings() {
  const saved = usePersona().data

  return (
    <SettingsSection title={label()} description={body()}>
      {saved === undefined ? (
        <Skeleton className="h-40 w-full" />
      ) : (
        <PersonaEditor saved={saved.text} />
      )}
    </SettingsSection>
  )
}

function PersonaEditor({ saved }: { saved: string }) {
  const save = useSavePersona()
  // What the box holds once it differs from the saved text; null until typed in.
  const [typed, setTyped] = useState<string | null>(null)
  const text = typed ?? saved
  const changed = typed !== null && typed.trim() !== saved

  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault()
        save.mutate(text, { onSuccess: () => setTyped(null) })
      }}
    >
      <Textarea
        aria-label={label()}
        value={text}
        rows={10}
        maxLength={20_000}
        onChange={(event) => setTyped(event.target.value)}
      />
      {save.isError ? (
        <Alert variant="destructive">
          <AlertDescription>
            {intl.formatMessage({
              id: "persona_save_error",
              defaultMessage: "The persona could not be saved.",
            })}
          </AlertDescription>
        </Alert>
      ) : null}
      <div className="flex items-center gap-3">
        <Button type="submit" disabled={!changed || save.isPending}>
          {intl.formatMessage({
            id: "persona_save_button",
            defaultMessage: "Save",
          })}
        </Button>
        {save.isSuccess && !changed ? (
          <span className="text-sm text-muted-foreground" role="status">
            {intl.formatMessage({
              id: "persona_saved_status",
              defaultMessage: "Saved",
            })}
          </span>
        ) : null}
      </div>
    </form>
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
