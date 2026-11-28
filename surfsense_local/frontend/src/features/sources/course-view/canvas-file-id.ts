const FILE_LINK = /\/courses\/\d+\/files\/(\d+)/

/** The Canvas file an address names, from its page, preview or download form. */
export function canvasFileId(href: string): number | null {
  const found = FILE_LINK.exec(href)
  return found ? Number(found[1]) : null
}
