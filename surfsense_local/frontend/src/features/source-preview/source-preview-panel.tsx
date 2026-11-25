import { useState } from "react"

import { Button } from "@/components/ui/button"
import { DetailPanel } from "@/components/ui/detail-panel"
import type { WorkspaceDocument } from "@/features/sources/api"
import { originalDocumentUrl } from "@/features/sources/api"
import { intl } from "@/i18n/intl"
import { getFileViewer } from "@/features/file-viewers/registry"
import { downloadsOriginals } from "@/features/sources/download-original"

import { TextReader } from "./text-reader"

export function SourcePreviewPanel({
  workspaceId,
  document,
  onOpen,
  onClose,
}: {
  workspaceId: number
  document: WorkspaceDocument
  onOpen: () => void
  onClose: () => void
}) {
  const [actionsContainer, setActionsContainer] =
    useState<HTMLDivElement | null>(null)
  const Viewer = getFileViewer(document.mime_type)
  const mimeType = document.mime_type
  const isFile = document.document_type === "FILE"

  return (
    <DetailPanel
      title={document.title}
      titleClassName="select-none"
      ariaLabel={intl.formatMessage({
        id: "source_preview_panel_aria",
        defaultMessage: "Source preview",
      })}
      closeLabel={intl.formatMessage({
        id: "source_preview_panel_close_aria",
        defaultMessage: "Close source preview",
      })}
      onClose={onClose}
      side="left"
      flush
      actions={
        <>
          <div ref={setActionsContainer} className="flex items-center gap-1" />
          {isFile ? (
            <Button
              variant="default"
              size="sm"
              className="h-6 px-1.5 text-[11px]"
              onClick={onOpen}
            >
              {downloadsOriginals()
                ? intl.formatMessage({
                    id: "source_preview_panel_download_file_button",
                    defaultMessage: "Download file",
                  })
                : intl.formatMessage({
                    id: "source_preview_panel_open_file_button",
                    defaultMessage: "Open file",
                  })}
            </Button>
          ) : null}
        </>
      }
    >
      <div className="h-full overflow-hidden">
        <div className="h-full">
          {Viewer && mimeType ? (
            // getFileViewer returns a stable registry reference.
            // eslint-disable-next-line react-hooks/static-components
            <Viewer
              url={originalDocumentUrl(workspaceId, document.id)}
              mimeType={mimeType}
              sizeBytes={null}
              title={document.title}
              actionsContainer={actionsContainer}
            />
          ) : (
            <TextReader workspaceId={workspaceId} document={document} />
          )}
        </div>
      </div>
    </DetailPanel>
  )
}
