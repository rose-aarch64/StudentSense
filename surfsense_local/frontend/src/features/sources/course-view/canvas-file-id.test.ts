import { describe, expect, it } from "vitest"

import { canvasFileId } from "./canvas-file-id"

describe("canvasFileId", () => {
  it("reads the file of an absolute or a relative Canvas link", () => {
    expect(
      canvasFileId("https://school.edu/courses/91884/files/1827589?wrap=1")
    ).toBe(1827589)
    expect(canvasFileId("/courses/91884/files/1827589")).toBe(1827589)
  })

  it("reads the same file from its preview and download forms", () => {
    expect(canvasFileId("/courses/1/files/5/preview?verifier=x")).toBe(5)
    expect(canvasFileId("/courses/1/files/5/download?download_frd=1")).toBe(5)
  })

  it("is null for a link that is not a Canvas file", () => {
    expect(canvasFileId("https://example.org/page")).toBeNull()
    expect(canvasFileId("/courses/1/pages/intro")).toBeNull()
    expect(canvasFileId("")).toBeNull()
  })
})
