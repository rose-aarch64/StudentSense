import { Button } from "@/components/ui/button"
import { intl } from "@/i18n/intl"

export type SourcesView = "files" | "modules"

/** Which way the Sources panel shows a synced class: its folders, or as Canvas lays it out. */
export function ViewSwitch({
  value,
  onChange,
}: {
  value: SourcesView
  onChange: (view: SourcesView) => void
}) {
  const choices: { view: SourcesView; label: string }[] = [
    {
      view: "files",
      label: intl.formatMessage({
        id: "sources_course_files_button",
        defaultMessage: "Files",
      }),
    },
    {
      view: "modules",
      label: intl.formatMessage({
        id: "sources_course_canvas_button",
        defaultMessage: "Canvas",
      }),
    },
  ]
  return (
    <div
      role="group"
      aria-label={intl.formatMessage({
        id: "sources_course_switch_aria",
        defaultMessage: "Show sources as",
      })}
      className="mb-2 flex shrink-0 gap-1"
    >
      {choices.map(({ view, label }) => (
        <Button
          key={view}
          type="button"
          size="sm"
          variant={value === view ? "secondary" : "ghost"}
          aria-pressed={value === view}
          className="touch:min-h-11"
          onClick={() => onChange(view)}
        >
          {label}
        </Button>
      ))}
    </div>
  )
}
