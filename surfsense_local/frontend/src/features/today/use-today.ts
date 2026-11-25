import { useState } from "react"

import { ApiError } from "@/lib/api"

import { askToday, type Turn } from "./api"

export type TodayFailure = "no_model" | "failed"

/** The window's own conversation: kept here, sent whole with each question. */
export function useToday() {
  const [turns, setTurns] = useState<Turn[]>([])
  const [pending, setPending] = useState(false)
  const [failure, setFailure] = useState<TodayFailure | null>(null)

  const ask = async (text: string) => {
    const question = text.trim()
    if (!question || pending) return
    setFailure(null)
    setPending(true)
    setTurns((all) => [...all, { role: "user", text: question }])
    try {
      const reply = await askToday(question, turns)
      setTurns((all) => [...all, { role: "assistant", text: reply.text }])
    } catch (error) {
      setFailure(
        error instanceof ApiError && error.status === 409
          ? "no_model"
          : "failed"
      )
    } finally {
      setPending(false)
    }
  }

  return { turns, pending, failure, ask }
}
