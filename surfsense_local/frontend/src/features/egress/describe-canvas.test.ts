import { describe, expect, it } from "vitest"

import { describeDestination } from "./api"

describe("the consent question for Canvas", () => {
  it("asks about reading Canvas, naming the school's host and promising it only reads", () => {
    const copy = describeDestination(
      "host:school.example",
      "school.example",
      "canvas"
    )

    expect(copy.label).toBe("school.example")
    expect(copy.title).toBe("Allow SurfSense to read your Canvas?")
    expect(copy.body).toContain("school.example")
    expect(copy.body).toContain("only reads")
  })

  it("names the hosts a course's files sit on, which one Allow switches on together", () => {
    const copy = describeDestination(
      "host:school.example",
      "school.example",
      "canvas",
      ["files.example"]
    )

    expect(copy.details).toContain(
      "Allowing also lets SurfSense reach files.example."
    )
  })
})
