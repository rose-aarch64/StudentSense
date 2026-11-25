const KEY = "surfsense:collapsed-folders:v1"

/** The folders left closed on this device; every folder is open until closed. */
export function readCollapsedFolders(): Set<number> {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(KEY) ?? "[]")
    return new Set(
      Array.isArray(stored)
        ? stored.filter((id): id is number => Number.isInteger(id))
        : []
    )
  } catch {
    return new Set()
  }
}

export function writeCollapsedFolders(ids: Set<number>) {
  try {
    localStorage.setItem(KEY, JSON.stringify([...ids]))
  } catch {
    // The folders still open and close for this session without storage.
  }
}
