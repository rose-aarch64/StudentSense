import { createContext, useContext } from "react"

export type CanvasFileLinks = {
  // The source a link's file became in this class, or null.
  documentIdFor: (href: string) => number | null
  open: (documentId: number) => void
}

export const CanvasFileLinksContext = createContext<CanvasFileLinks | null>(
  null
)

/** Null where no class's files are known, so a link behaves as it always did. */
export function useCanvasFileLinks(): CanvasFileLinks | null {
  return useContext(CanvasFileLinksContext)
}
