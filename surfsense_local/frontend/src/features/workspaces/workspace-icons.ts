import type { ComponentType } from "react"

import {
  AtomIcon,
  BankIcon,
  Book02Icon,
  BookOpen01Icon,
  Brain02Icon,
  Briefcase01Icon,
  CalculatorIcon,
  Camera01Icon,
  ChartLineData01Icon,
  CodeIcon,
  ComputerIcon,
  DnaIcon,
  EarthIcon,
  Flag01Icon,
  GraduationScrollIcon,
  Home01Icon,
  LanguageSquareIcon,
  LaptopIcon,
  Leaf01Icon,
  LibraryIcon,
  MapsIcon,
  Mortarboard01Icon,
  MusicNote01Icon,
  PaintBrush01Icon,
  Rocket01Icon,
  SchoolIcon,
  Shield01Icon,
  StarIcon,
  Sword01Icon,
  TestTube01Icon,
} from "@/components/ui/icons"

type IconComponent = ComponentType<{ className?: string }>

// What a workspace may be marked with, by the key the API stores. Keys are kept
// once released: a stored key the set no longer has simply shows initials.
const ICONS: Record<string, IconComponent> = {
  "book-open": BookOpen01Icon,
  book: Book02Icon,
  "test-tube": TestTube01Icon,
  computer: ComputerIcon,
  laptop: LaptopIcon,
  code: CodeIcon,
  camera: Camera01Icon,
  earth: EarthIcon,
  music: MusicNote01Icon,
  calculator: CalculatorIcon,
  shield: Shield01Icon,
  brush: PaintBrush01Icon,
  atom: AtomIcon,
  library: LibraryIcon,
  mortarboard: Mortarboard01Icon,
  scroll: GraduationScrollIcon,
  leaf: Leaf01Icon,
  rocket: Rocket01Icon,
  flag: Flag01Icon,
  star: StarIcon,
  dna: DnaIcon,
  language: LanguageSquareIcon,
  home: Home01Icon,
  briefcase: Briefcase01Icon,
  bank: BankIcon,
  map: MapsIcon,
  sword: Sword01Icon,
  brain: Brain02Icon,
  chart: ChartLineData01Icon,
  school: SchoolIcon,
}

/** The keys the icon dialog offers, in its order. */
export const WORKSPACE_ICON_KEYS: readonly string[] = Object.keys(ICONS)

/** The icon a key names, or null for no key or one this release does not know. */
export function workspaceIcon(key: string | null): IconComponent | null {
  return key !== null && Object.hasOwn(ICONS, key) ? ICONS[key] : null
}
