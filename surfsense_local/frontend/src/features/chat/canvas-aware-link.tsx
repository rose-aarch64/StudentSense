import type { ComponentProps } from "react"
import { defaultComponents } from "streamdown"

import { useCanvasFileLinks } from "@/features/sources/course-view/canvas-file-links-context"

const DefaultLink = defaultComponents.a

/**
 * A markdown link. One to a Canvas file the class holds opens that source in the
 * app; every other link is Streamdown's own, with its safety check.
 */
export function CanvasAwareLink(props: ComponentProps<"a">) {
  const canvasFiles = useCanvasFileLinks()
  const documentId = canvasFiles?.documentIdFor(props.href ?? "") ?? null
  if (!canvasFiles || documentId === null) return <DefaultLink {...props} />
  return (
    <a
      href={props.href}
      className="font-medium wrap-anywhere text-primary underline"
      onClick={(event) => {
        // Ctrl, Cmd or Shift asks for a new tab or window: that stays Canvas's.
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey)
          return
        event.preventDefault()
        canvasFiles.open(documentId)
      }}
    >
      {props.children}
    </a>
  )
}
