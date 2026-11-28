import { useEffect, useState } from "react"

import { getCourseView, type CourseView } from "./course-api"

/**
 * A class's modules, read again whenever `refreshKey` changes (the caller
 * passes something that changes when its documents do, so a finished sync shows).
 * A failed read is no view: the Sources panel then simply has no Modules switch.
 */
export function useCourseView(
  workspaceId: number,
  refreshKey: unknown
): { view: CourseView | null; isLoading: boolean } {
  const [state, setState] = useState<{
    workspaceId: number
    view: CourseView | null
    isLoading: boolean
  }>({ workspaceId, view: null, isLoading: true })

  useEffect(() => {
    const controller = new AbortController()
    getCourseView(workspaceId, controller.signal)
      .then((view) => setState({ workspaceId, view, isLoading: false }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return
        setState({ workspaceId, view: null, isLoading: false })
      })
    return () => controller.abort()
  }, [workspaceId, refreshKey])

  // A view read for another workspace is not this one's.
  return state.workspaceId === workspaceId
    ? { view: state.view, isLoading: state.isLoading }
    : { view: null, isLoading: true }
}
