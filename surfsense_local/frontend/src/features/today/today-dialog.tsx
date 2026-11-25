import { useState, type FormEvent } from "react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { CitationChunkText } from "@/features/chat/citation-chunk-text"
import { intl } from "@/i18n/intl"
import { cn } from "@/lib/utils"

import { useToday } from "./use-today"

/** A chat outside every workspace: it reads the whole to-do list and plans the day. */
export function TodayDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { turns, pending, failure, ask } = useToday()
  const [draft, setDraft] = useState("")
  const dayQuestion = intl.formatMessage({
    id: "today_quick_button",
    defaultMessage: "What’s going on today?",
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    void ask(draft)
    setDraft("")
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex h-[min(40rem,calc(100dvh-2rem))] flex-col sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>
            {intl.formatMessage({
              id: "today_dialog_title",
              defaultMessage: "Today",
            })}
          </DialogTitle>
          <DialogDescription className="text-pretty">
            {intl.formatMessage({
              id: "today_dialog_body",
              defaultMessage:
                "Ask about your day. It reads your to-dos across every workspace and suggests a plan. It does not change anything.",
            })}
          </DialogDescription>
        </DialogHeader>
        <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto">
          {turns.length === 0 ? (
            <div>
              <Button
                type="button"
                variant="outline"
                disabled={pending}
                onClick={() => void ask(dayQuestion)}
              >
                {dayQuestion}
              </Button>
            </div>
          ) : (
            turns.map((turn, at) => (
              <div
                key={at}
                className={cn(
                  "max-w-[85%] rounded-lg px-3 py-2 text-sm select-text",
                  turn.role === "user"
                    ? "self-end bg-primary text-primary-foreground"
                    : "self-start bg-muted"
                )}
              >
                {turn.role === "user" ? (
                  turn.text
                ) : (
                  <CitationChunkText content={turn.text} />
                )}
              </div>
            ))
          )}
          {pending ? (
            <p className="text-sm text-muted-foreground" role="status">
              {intl.formatMessage({
                id: "today_thinking_status",
                defaultMessage: "Thinking…",
              })}
            </p>
          ) : null}
          {failure ? (
            <p className="text-sm text-destructive" role="alert">
              {failure === "no_model"
                ? intl.formatMessage({
                    id: "today_error_no_model",
                    defaultMessage: "Choose a chat model in Settings first.",
                  })
                : intl.formatMessage({
                    id: "today_error_failed",
                    defaultMessage: "The answer could not be fetched.",
                  })}
            </p>
          ) : null}
        </div>
        <form className="flex gap-2" onSubmit={submit}>
          <Input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            aria-label={intl.formatMessage({
              id: "today_ask_placeholder",
              defaultMessage: "Ask about today",
            })}
            placeholder={intl.formatMessage({
              id: "today_ask_placeholder",
              defaultMessage: "Ask about today",
            })}
          />
          <Button type="submit" disabled={pending || draft.trim() === ""}>
            {intl.formatMessage({
              id: "today_ask_button",
              defaultMessage: "Ask",
            })}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}
