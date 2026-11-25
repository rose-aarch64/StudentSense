import { requestJson } from "@/lib/api"

// The backend's /today route, as `modules/today/schemas.py` returns it.

export type Turn = { role: "user" | "assistant"; text: string }

/** The time on the user's clock with its offset, such as 2026-11-24T09:30:00-05:00. */
export function localIsoNow(at = new Date()): string {
  const pad = (n: number) => String(Math.trunc(Math.abs(n))).padStart(2, "0")
  const offset = -at.getTimezoneOffset()
  const sign = offset < 0 ? "-" : "+"
  const date = `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}`
  const time = `${pad(at.getHours())}:${pad(at.getMinutes())}:${pad(at.getSeconds())}`
  return `${date}T${time}${sign}${pad(offset / 60)}:${pad(offset % 60)}`
}

export function askToday(
  text: string,
  history: Turn[],
  signal?: AbortSignal
): Promise<{ text: string }> {
  return requestJson<{ text: string }>("/today/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, now: localIsoNow(), history }),
    signal,
  })
}
