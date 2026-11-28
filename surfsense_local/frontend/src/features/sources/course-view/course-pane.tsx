import { useState } from "react"

import { Button } from "@/components/ui/button"
import { TextReader } from "@/features/source-preview/text-reader"
import { intl } from "@/i18n/intl"

import type { WorkspaceDocument } from "../api"
import type { Tick } from "../tree/scope-state"
import type { CourseView } from "./course-api"
import { ModulesView } from "./modules-view"
import { TextbookSection } from "./textbook-section"

type NoteSection = "syllabus" | "announcements" | "assignments" | "links"
type Section = "modules" | "textbook" | NoteSection

/** What the Canvas switch shows: Canvas's menu as tabs, each shown in place. */
export function CoursePane({
  view,
  workspaceId,
  documents,
  selectedDocumentIds,
  folderTicks,
  onSelectionChange,
  onFolderSelectionChange,
  onPreview,
  onImported,
}: {
  view: CourseView
  workspaceId: number
  documents: readonly WorkspaceDocument[]
  selectedDocumentIds: readonly number[]
  folderTicks: ReadonlyMap<number, Tick>
  onSelectionChange: (documentId: number, selected: boolean) => void
  onFolderSelectionChange: (folderId: number, selected: boolean) => void
  onPreview: (documentId: number) => void
  onImported: () => void
}) {
  const [section, setSection] = useState<Section>("modules")
  const readyDocumentIds = new Set(
    documents.filter((d) => d.status === "ready").map((d) => d.id)
  )
  const textbookFolder = view.textbook_folder_id
  const tabs: { key: Section; label: string }[] = [
    {
      key: "modules",
      label: intl.formatMessage({
        id: "sources_course_modules_button",
        defaultMessage: "Modules",
      }),
    },
    {
      key: "syllabus",
      label: intl.formatMessage({
        id: "sources_course_syllabus_button",
        defaultMessage: "Syllabus",
      }),
    },
    {
      key: "announcements",
      label: intl.formatMessage({
        id: "sources_course_announcements_button",
        defaultMessage: "Announcements",
      }),
    },
    {
      key: "assignments",
      label: intl.formatMessage({
        id: "sources_course_assignments_button",
        defaultMessage: "Assignments",
      }),
    },
    {
      key: "textbook",
      label: intl.formatMessage({
        id: "sources_textbook_title",
        defaultMessage: "Textbook",
      }),
    },
    {
      key: "links",
      label: intl.formatMessage({
        id: "sources_course_links_button",
        defaultMessage: "Links",
      }),
    },
  ]
  // A tab is offered only when there is something behind it.
  const shown = tabs.filter((tab) =>
    tab.key === "modules"
      ? true
      : tab.key === "textbook"
        ? textbookFolder !== null
        : view.notes[tab.key] !== undefined
  )
  const noteId = section in view.notes ? view.notes[section] : undefined
  const note = documents.find((d) => d.id === noteId)

  return (
    <div className="flex flex-col gap-3">
      {/* Scrolls inside itself, so a phone's page never scrolls sideways. */}
      <div className="flex gap-1.5 overflow-x-auto pb-1">
        {shown.map((tab) => (
          <Button
            key={tab.key}
            type="button"
            size="sm"
            variant={section === tab.key ? "secondary" : "outline"}
            aria-pressed={section === tab.key}
            className="shrink-0 touch:min-h-11"
            onClick={() => setSection(tab.key)}
          >
            {tab.label}
          </Button>
        ))}
      </div>
      {section === "textbook" && textbookFolder !== null ? (
        <TextbookSection
          workspaceId={workspaceId}
          folderId={textbookFolder}
          documents={documents.filter((d) => d.folder_id === textbookFolder)}
          selectedDocumentIds={selectedDocumentIds}
          onSelectionChange={onSelectionChange}
          onPreview={onPreview}
          onImported={onImported}
        />
      ) : note !== undefined ? (
        <TextReader key={note.id} workspaceId={workspaceId} document={note} />
      ) : (
        <ModulesView
          view={view}
          readyDocumentIds={readyDocumentIds}
          selectedDocumentIds={selectedDocumentIds}
          folderTicks={folderTicks}
          onSelectionChange={onSelectionChange}
          onFolderSelectionChange={onFolderSelectionChange}
          onPreview={onPreview}
        />
      )}
    </div>
  )
}
