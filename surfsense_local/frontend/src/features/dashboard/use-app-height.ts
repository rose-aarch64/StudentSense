import { useEffect } from "react"

/**
 * Sizes the page to what is visible, as `--app-height`, so an on-screen
 * keyboard shrinks it and the composer stays above the keys instead of under
 * them. The page's own `100svh` applies while nothing sets this.
 */
export function useAppHeight(active: boolean) {
  useEffect(() => {
    const viewport = window.visualViewport
    if (!active || !viewport) return
    const root = document.documentElement
    const follow = () =>
      root.style.setProperty("--app-height", `${viewport.height}px`)
    follow()
    viewport.addEventListener("resize", follow)
    return () => {
      viewport.removeEventListener("resize", follow)
      root.style.removeProperty("--app-height")
    }
  }, [active])
}
