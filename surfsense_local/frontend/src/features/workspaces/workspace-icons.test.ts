import { describe, expect, it } from "vitest"

import { WORKSPACE_ICON_KEYS, workspaceIcon } from "./workspace-icons"

describe("workspace icons", () => {
  it("resolves a key the set offers", () => {
    expect(workspaceIcon("camera")).not.toBeNull()
  })

  it("shows nothing for a key a later release added, or none at all", () => {
    expect(workspaceIcon("future-icon")).toBeNull()
    expect(workspaceIcon(null)).toBeNull()
  })

  it("offers only slugs the API accepts, each with an icon", () => {
    expect(WORKSPACE_ICON_KEYS.length).toBeGreaterThanOrEqual(24)
    for (const key of WORKSPACE_ICON_KEYS) {
      expect(key).toMatch(/^[a-z0-9-]{1,32}$/)
      expect(workspaceIcon(key)).not.toBeNull()
    }
  })
})
