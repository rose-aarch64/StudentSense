import type { ComponentType } from "react"

import { PdfViewer } from "./pdf-viewer"
import { PptxViewer } from "./pptx-viewer"

export type FileViewerProps = {
  url: string
  mimeType: string
  sizeBytes: number | null
  title: string
  actionsContainer: HTMLElement | null
}

const FILE_VIEWERS: Record<string, ComponentType<FileViewerProps>> = {
  "application/pdf": PdfViewer,
  "application/vnd.openxmlformats-officedocument.presentationml.presentation":
    PptxViewer,
}

export function getFileViewer(
  mimeType: string | null
): ComponentType<FileViewerProps> | null {
  return mimeType ? (FILE_VIEWERS[mimeType] ?? null) : null
}
