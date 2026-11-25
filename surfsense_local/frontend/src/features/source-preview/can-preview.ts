import { getFileViewer } from "@/features/file-viewers/registry"
import type { WorkspaceDocument } from "@/features/sources/api"

/** A file with a viewer shows its original before it is read; any other source needs its text. */
export function canPreview(document: WorkspaceDocument): boolean {
  return (
    getFileViewer(document.mime_type) !== null || document.status === "ready"
  )
}
