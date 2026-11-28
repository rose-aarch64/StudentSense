import { useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { intl } from "@/i18n/intl"

import { uploadDocuments, type WorkspaceDocument } from "../api"

// The book formats SurfSense reads; the server stays the judge.
const BOOK_ACCEPT = ".pdf,.epub,.mobi,.azw3"

export function TextbookSection({
  workspaceId,
  folderId,
  documents,
  selectedDocumentIds,
  onSelectionChange,
  onPreview,
  onImported,
}: {
  workspaceId: number
  folderId: number
  // The books already in the folder.
  documents: WorkspaceDocument[]
  selectedDocumentIds: readonly number[]
  onSelectionChange: (documentId: number, selected: boolean) => void
  onPreview: (documentId: number) => void
  onImported: () => void
}) {
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)
  const selected = new Set(selectedDocumentIds)

  async function importBooks(files: File[]) {
    if (files.length === 0) return
    setBusy(true)
    setFailed(false)
    try {
      const outcome = await uploadDocuments(workspaceId, files, undefined, {
        folderId,
      })
      if (outcome.rejected.length > 0) setFailed(true)
      onImported()
    } catch {
      setFailed(true)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="flex flex-col gap-2">
      <div className="flex min-h-9 items-center justify-between gap-2 touch:min-h-11">
        <h3 className="text-sm font-medium">
          {intl.formatMessage({
            id: "sources_textbook_title",
            defaultMessage: "Textbook",
          })}
        </h3>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          className="touch:min-h-11"
          disabled={busy}
          onClick={() => input.current?.click()}
        >
          {intl.formatMessage({
            id: "sources_textbook_import_button",
            defaultMessage: "Import textbook",
          })}
        </Button>
        <input
          ref={input}
          type="file"
          multiple
          hidden
          accept={BOOK_ACCEPT}
          onChange={(event) => {
            const files = Array.from(event.target.files ?? [])
            event.target.value = ""
            void importBooks(files)
          }}
        />
      </div>
      {failed ? (
        <p role="alert" className="text-sm text-destructive">
          {intl.formatMessage({
            id: "sources_textbook_import_error",
            defaultMessage: "The textbook could not be imported",
          })}
        </p>
      ) : null}
      {documents.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          {intl.formatMessage({
            id: "sources_textbook_empty",
            defaultMessage: "No textbook yet.",
          })}
        </p>
      ) : (
        <ul className="rounded-lg border">
          {documents.map((document) => (
            <li
              key={document.id}
              className="flex min-h-9 items-center gap-2 border-t px-2 py-1 text-sm first:border-t-0 touch:min-h-11"
            >
              {document.status === "ready" ? (
                <Checkbox
                  checked={selected.has(document.id)}
                  aria-label={intl.formatMessage(
                    {
                      id: "sources_row_select_aria",
                      defaultMessage: "Select {title}",
                    },
                    { title: document.title }
                  )}
                  onCheckedChange={(next) =>
                    onSelectionChange(document.id, next === true)
                  }
                />
              ) : (
                <span className="size-4 shrink-0" aria-hidden />
              )}
              <Button
                variant="bare"
                type="button"
                className="h-auto min-w-0 flex-1 justify-start text-left font-normal break-words whitespace-normal hover:underline"
                onClick={() => onPreview(document.id)}
              >
                {document.title}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
