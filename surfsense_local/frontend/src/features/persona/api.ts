import { requestJson } from "@/lib/api"

// The backend's /persona routes, as `modules/persona/router.py` returns them.

export type Persona = { text: string }

export function readPersona(signal?: AbortSignal): Promise<Persona> {
  return requestJson<Persona>("/persona", { signal })
}

export function writePersona(text: string): Promise<Persona> {
  return requestJson<Persona>("/persona", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  })
}
