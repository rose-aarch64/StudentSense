import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it } from "vitest"

import { NeedsSyncLine } from "./needs-sync-line"

afterEach(cleanup)

describe("needs-sync line", () => {
  it("tells a class with no outline yet where to sync", () => {
    render(<NeedsSyncLine />)

    expect(
      screen.getByText(
        "Run Sync now in Settings › Canvas to see this class’s modules."
      )
    ).toBeTruthy()
  })
})
