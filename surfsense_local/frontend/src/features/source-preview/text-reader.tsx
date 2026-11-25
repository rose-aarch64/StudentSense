import { useQuery } from "@tanstack/react-query"

import { Skeleton } from "@/components/ui/skeleton"
import { CitationChunkText } from "@/features/chat/citation-chunk-text"
import { getDocument, type WorkspaceDocument } from "@/features/sources/api"
import { intl } from "@/i18n/intl"

/** A source's extracted text, formatted, with no editing step. */
export function TextReader({
  workspaceId,
  document,
}: {
  workspaceId: number
  document: WorkspaceDocument
}) {
  const query = useQuery({
    queryKey: ["source-text", workspaceId, document.id, document.updated_at],
    queryFn: ({ signal }) => getDocument(workspaceId, document.id, signal),
  })

  if (query.isPending) {
    return <Skeleton className="m-4 h-24" />
  }
  const content = query.data?.content?.trim()
  return (
    <div className="h-full overflow-y-auto px-4 py-3 select-text">
      {query.isError || !content ? (
        <p className="text-sm text-muted-foreground">
          {intl.formatMessage({
            id: "source_preview_no_text_empty",
            defaultMessage: "This source has no text to show",
          })}
        </p>
      ) : (
        <CitationChunkText content={content} />
      )}
    </div>
  )
}
