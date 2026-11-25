import { useSyncExternalStore } from "react"

/**
 * Below this width the desktop layout cannot fit: its columns need 1328 px.
 * The one place a phone width is named.
 */
export const COMPACT_BELOW_PX = 1024

const COMPACT_QUERY = `(max-width: ${COMPACT_BELOW_PX - 1}px)`

function subscribe(onChange: () => void) {
  const query = window.matchMedia?.(COMPACT_QUERY)
  query?.addEventListener("change", onChange)
  return () => query?.removeEventListener("change", onChange)
}

function compactNow() {
  return window.matchMedia?.(COMPACT_QUERY).matches ?? false
}

/** Whether the window is narrower than the desktop layout can fit. */
export function useCompactLayout(): boolean {
  return useSyncExternalStore(subscribe, compactNow, () => false)
}
