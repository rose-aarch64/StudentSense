import { useState } from "react"
import type { UseMutationResult } from "@tanstack/react-query"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { intl } from "@/i18n/intl"

import type { Persona } from "./api"

/** A persona's box with its Save button, for the shared persona and the agent's. */
export function PersonaEditor({
  label,
  saved,
  save,
}: {
  label: string
  saved: string
  save: UseMutationResult<Persona, Error, string>
}) {
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
        aria-label={label}
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
