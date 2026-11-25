import { afterEach, describe, expect, it, vi } from "vitest"

import {
  readCollapsedFolders,
  writeCollapsedFolders,
} from "./collapsed-folders"

afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})

describe("collapsed folders", () => {
  it("starts with every folder open", () => {
    expect(readCollapsedFolders().size).toBe(0)
  })

  it("remembers which folders were closed", () => {
    writeCollapsedFolders(new Set([3, 8]))

    expect([...readCollapsedFolders()].sort()).toEqual([3, 8])
  })

  it("ignores stored text that is not a list of ids", () => {
    localStorage.setItem("surfsense:collapsed-folders:v1", '{"a":1}')

    expect(readCollapsedFolders().size).toBe(0)
  })

  it("keeps working when storage is unavailable", () => {
    vi.stubGlobal("localStorage", {
      getItem: () => {
        throw new Error("denied")
      },
      setItem: () => {
        throw new Error("denied")
      },
    })

    expect(readCollapsedFolders().size).toBe(0)
    expect(() => writeCollapsedFolders(new Set([1]))).not.toThrow()
  })
})
