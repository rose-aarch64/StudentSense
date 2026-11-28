import { renderHook, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { CourseView } from "./course-api"
import { useCourseView } from "./use-course-view"

const api = vi.hoisted(() => ({ getCourseView: vi.fn() }))
vi.mock("./course-api", () => ({ getCourseView: api.getCourseView }))

const SYNCED: CourseView = {
  synced: true,
  needs_sync: false,
  textbook_folder_id: 9,
  notes: {},
  files: {},
  modules: [],
}

beforeEach(() => {
  api.getCourseView.mockReset()
})

describe("course view data", () => {
  it("returns what the route sends for the workspace", async () => {
    api.getCourseView.mockResolvedValue(SYNCED)

    const { result } = renderHook(() => useCourseView(2, 0))

    await waitFor(() => expect(result.current.view).toEqual(SYNCED))
    expect(api.getCourseView.mock.calls[0]![0]).toBe(2)
  })

  it("has no view, and does not throw, when the request fails", async () => {
    api.getCourseView.mockRejectedValue(new Error("down"))

    const { result } = renderHook(() => useCourseView(2, 0))

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.view).toBeNull()
  })

  it("asks again when the refresh key changes, as after a sync", async () => {
    api.getCourseView.mockResolvedValue(SYNCED)

    const { rerender } = renderHook(({ key }) => useCourseView(2, key), {
      initialProps: { key: 1 },
    })
    await waitFor(() => expect(api.getCourseView).toHaveBeenCalledTimes(1))
    rerender({ key: 2 })

    await waitFor(() => expect(api.getCourseView).toHaveBeenCalledTimes(2))
  })
})
