import { Button } from "@/components/ui/button"
import { Menu01Icon, Task01Icon } from "@/components/ui/icons"
import { intl } from "@/i18n/intl"

/** The chat header's button that opens the phone's drawer. */
export function CompactMenuButton({ onClick }: { onClick: () => void }) {
  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-lg"
      aria-label={intl.formatMessage({
        id: "dashboard_compact_menu_aria",
        defaultMessage: "Open menu",
      })}
      onClick={onClick}
    >
      <Menu01Icon />
    </Button>
  )
}

/** The chat header's shortcut to the to-do list, one of the phone's two uses. */
export function CompactTodoButton({ onClick }: { onClick: () => void }) {
  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-lg"
      aria-label={intl.formatMessage({
        id: "dashboard_footer_todos_button",
        defaultMessage: "To-do",
      })}
      onClick={onClick}
    >
      <Task01Icon />
    </Button>
  )
}
