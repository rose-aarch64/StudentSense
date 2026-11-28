import { useMemo, type ReactNode } from "react"

import { canvasFileId } from "./canvas-file-id"
import {
  CanvasFileLinksContext,
  type CanvasFileLinks,
} from "./canvas-file-links-context"

/** Lets a note's link to a Canvas file open the source the file became. */
export function CanvasFileLinksProvider({
  files,
  onOpen,
  children,
}: {
  // Canvas file id (as a JSON key) -> document id.
  files: Record<string, number>
  onOpen: (documentId: number) => void
  children: ReactNode
}) {
  const value = useMemo<CanvasFileLinks>(
    () => ({
      documentIdFor: (href) => {
        const id = canvasFileId(href)
        return id === null ? null : (files[String(id)] ?? null)
      },
      open: onOpen,
    }),
    [files, onOpen]
  )
  return (
    <CanvasFileLinksContext.Provider value={value}>
      {children}
    </CanvasFileLinksContext.Provider>
  )
}
