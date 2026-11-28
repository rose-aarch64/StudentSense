import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { intl } from "@/i18n/intl"

import type { Tick } from "../tree/scope-state"
import type { CourseView, ItemView, ModuleView } from "./course-api"

const HEADER_TYPES = new Set(["SubHeader"])

export function ModulesView({
  view,
  readyDocumentIds,
  selectedDocumentIds,
  folderTicks,
  onSelectionChange,
  onFolderSelectionChange,
  onPreview,
}: {
  view: CourseView
  // Only a ready source can be ticked, as in the Files view.
  readyDocumentIds: ReadonlySet<number>
  selectedDocumentIds: readonly number[]
  folderTicks: ReadonlyMap<number, Tick>
  onSelectionChange: (documentId: number, selected: boolean) => void
  onFolderSelectionChange: (folderId: number, selected: boolean) => void
  onPreview: (documentId: number) => void
}) {
  const selected = new Set(selectedDocumentIds)
  return (
    <div className="flex flex-col gap-3 pb-2">
      {view.modules.map((module) => {
        const rowIds = tickableIds(module, readyDocumentIds)
        return (
          <ModuleBlock
            key={module.id}
            module={module}
            tick={
              module.folder_id === null
                ? null
                : moduleTick(
                    folderTicks.get(module.folder_id) ?? "unchecked",
                    rowIds,
                    selected
                  )
            }
            readyDocumentIds={readyDocumentIds}
            selected={selected}
            onSelectionChange={onSelectionChange}
            onModuleSelectionChange={(folderId, next) => {
              onFolderSelectionChange(folderId, next)
              // An item two modules hold is filed in the first one's folder only.
              for (const id of rowIds) {
                if (selected.has(id) !== next) onSelectionChange(id, next)
              }
            }}
            onPreview={onPreview}
          />
        )
      })}
    </div>
  )
}

function tickableIds(
  module: ModuleView,
  readyDocumentIds: ReadonlySet<number>
): number[] {
  return module.items.flatMap((item) =>
    item.document_id !== null && readyDocumentIds.has(item.document_id)
      ? [item.document_id]
      : []
  )
}

// The folder's tick, made mixed by any row it shows that disagrees with it.
function moduleTick(
  folderTick: Tick,
  rowIds: readonly number[],
  selected: ReadonlySet<number>
): Tick {
  const anyIn =
    folderTick !== "unchecked" || rowIds.some((id) => selected.has(id))
  const anyOut =
    folderTick !== "checked" || rowIds.some((id) => !selected.has(id))
  return anyIn && anyOut ? "mixed" : anyIn ? "checked" : "unchecked"
}

function ModuleBlock({
  module,
  tick,
  readyDocumentIds,
  selected,
  onSelectionChange,
  onModuleSelectionChange,
  onPreview,
}: {
  module: ModuleView
  tick: Tick | null
  readyDocumentIds: ReadonlySet<number>
  selected: ReadonlySet<number>
  onSelectionChange: (documentId: number, selected: boolean) => void
  onModuleSelectionChange: (folderId: number, selected: boolean) => void
  onPreview: (documentId: number) => void
}) {
  return (
    <section className="overflow-hidden rounded-lg border">
      {/* No fill: the tick box's border is as light as a muted fill and would vanish. */}
      <div className="flex min-h-9 items-center gap-2 px-2 touch:min-h-11">
        {tick !== null && module.folder_id !== null ? (
          <Checkbox
            checked={tick === "checked"}
            indeterminate={tick === "mixed"}
            aria-label={intl.formatMessage(
              {
                id: "sources_modules_select_module_aria",
                defaultMessage: "Select module {name}",
              },
              { name: module.name }
            )}
            onCheckedChange={() =>
              onModuleSelectionChange(module.folder_id!, tick !== "checked")
            }
          />
        ) : null}
        <h3 className="min-w-0 flex-1 text-sm font-medium break-words">
          {module.name}
        </h3>
      </div>
      <ul>
        {module.items.map((item, index) => (
          <ItemRow
            key={index}
            item={item}
            ready={
              item.document_id !== null &&
              readyDocumentIds.has(item.document_id)
            }
            checked={
              item.document_id !== null && selected.has(item.document_id)
            }
            onSelectionChange={onSelectionChange}
            onPreview={onPreview}
          />
        ))}
      </ul>
    </section>
  )
}

function ItemRow({
  item,
  ready,
  checked,
  onSelectionChange,
  onPreview,
}: {
  item: ItemView
  ready: boolean
  checked: boolean
  onSelectionChange: (documentId: number, selected: boolean) => void
  onPreview: (documentId: number) => void
}) {
  if (HEADER_TYPES.has(item.type)) {
    return (
      <li className="border-t bg-muted/40 px-3 py-1 text-xs font-medium break-words text-muted-foreground">
        {item.title}
      </li>
    )
  }
  const documentId = item.document_id
  return (
    <li className="flex min-h-9 items-center gap-2 border-t px-2 py-1 text-sm touch:min-h-11">
      {documentId !== null && ready ? (
        <Checkbox
          checked={checked}
          aria-label={intl.formatMessage(
            { id: "sources_row_select_aria", defaultMessage: "Select {title}" },
            { title: item.title }
          )}
          onCheckedChange={(next) =>
            onSelectionChange(documentId, next === true)
          }
        />
      ) : (
        <span className="size-4 shrink-0" aria-hidden />
      )}
      <span className="min-w-0 flex-1 break-words">
        <ItemTitle item={item} onPreview={onPreview} />
      </span>
      <ItemMeta item={item} />
    </li>
  )
}

function ItemTitle({
  item,
  onPreview,
}: {
  item: ItemView
  onPreview: (documentId: number) => void
}) {
  if (item.document_id !== null) {
    const documentId = item.document_id
    return (
      <Button
        variant="bare"
        type="button"
        className="h-auto min-w-0 justify-start text-left font-normal break-words whitespace-normal hover:underline"
        onClick={() => onPreview(documentId)}
      >
        {item.title}
      </Button>
    )
  }
  if (item.url !== null) {
    return (
      <a
        href={item.url}
        target="_blank"
        rel="noreferrer noopener"
        className="break-words underline underline-offset-2"
      >
        {item.title}
        <span className="ml-1.5 text-xs text-muted-foreground">
          {hostOf(item.url)}
        </span>
      </a>
    )
  }
  return <>{item.title}</>
}

function ItemMeta({ item }: { item: ItemView }) {
  if (item.due_at === null && item.points === null) return null
  return (
    <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
      {item.due_at !== null
        ? intl.formatDate(item.due_at, { month: "short", day: "numeric" })
        : null}
      {item.due_at !== null && item.points !== null ? " " : null}
      {item.points !== null
        ? intl.formatMessage(
            {
              id: "sources_modules_points_label",
              defaultMessage: "{points, number} pts",
            },
            { points: item.points }
          )
        : null}
    </span>
  )
}

function hostOf(url: string): string {
  try {
    return new URL(url).host
  } catch {
    return ""
  }
}
