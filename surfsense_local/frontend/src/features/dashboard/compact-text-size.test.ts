import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"

import { COMPACT_BELOW_PX } from "./use-compact-layout"

const css = readFileSync(join(__dirname, "../../index.css"), "utf8")

describe("the text size on a phone", () => {
  it("is the browser's 100%, where the desktop runs 125%", () => {
    expect(css).toMatch(/html\s*\{[^}]*font-size:\s*125%/)

    const phone = css.match(
      /@media \(max-width: (\d+)px\)\s*\{\s*html\s*\{\s*font-size:\s*100%/
    )
    expect(phone).not.toBeNull()
  })

  it("starts at the width where the layout turns compact", () => {
    const phone = css.match(
      /@media \(max-width: (\d+)px\)\s*\{\s*html\s*\{\s*font-size:\s*100%/
    )

    expect(Number(phone?.[1])).toBe(COMPACT_BELOW_PX - 1)
  })
})
