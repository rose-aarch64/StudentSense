import { requestJson } from "@/lib/api"

export type ItemView = {
  type: string
  title: string
  // The source the item became: a page, a file or an assignment.
  document_id: number | null
  // Where a link goes.
  url: string | null
  due_at: string | null
  points: number | null
}

export type ModuleView = {
  id: number
  name: string
  // The folder holding the module's sources; null when it holds none.
  folder_id: number | null
  items: ItemView[]
}

/** A synced class laid out as Canvas lays out its Modules page. */
export type CourseView = {
  // False for a workspace Canvas did not make, and for a class that needs one more sync.
  synced: boolean
  // A Canvas class with no outline yet: one sync makes it.
  needs_sync: boolean
  textbook_folder_id: number | null
  // The Overview notes by name: syllabus, announcements, assignments, links.
  notes: Record<string, number>
  // Canvas file id -> the source it became, for the links in the class's notes.
  files: Record<string, number>
  modules: ModuleView[]
}

export function getCourseView(
  workspaceId: number,
  signal?: AbortSignal
): Promise<CourseView> {
  return requestJson<CourseView>(`/canvas/workspaces/${workspaceId}/course`, {
    signal,
  })
}
