import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { intl } from "@/i18n/intl"
import { cn } from "@/lib/utils"

import type { ContextUsage } from "../api"
import { contextPercent } from "./context-percent"

/** How full the chat's history is. Nothing without a budget to measure against. */
export function ContextGauge({
  usage,
  agentic = false,
  className,
}: {
  usage: ContextUsage | null
  // At 100% an agent's memory is full and it has to summarise its earlier
  // work; a chat stops sending its oldest messages.
  agentic?: boolean
  className?: string
}) {
  if (usage === null || usage.budget === null || usage.budget <= 0) return null
  const percent = contextPercent(usage.used, usage.budget) / 100
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Button
            variant="bare"
            type="button"
            aria-label={intl.formatMessage(
              {
                id: "chat_context_gauge_aria",
                defaultMessage: "History used: {percent, number, ::percent}",
              },
              { percent }
            )}
            className={cn(
              "px-1.5 py-1 text-[11px] font-normal text-muted-foreground tabular-nums select-none",
              className
            )}
          />
        }
      >
        {intl.formatMessage(
          {
            id: "chat_context_gauge_label",
            defaultMessage: "{percent, number, ::percent}",
          },
          { percent }
        )}
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-72">
        {agentic
          ? intl.formatMessage(
              {
                id: "chat_context_gauge_agent_tooltip",
                defaultMessage:
                  "Tokens in the agent’s memory: {used, number} of {budget, number}. At 100%, its memory is full and the agent has to summarize the earlier work to go on.",
              },
              { used: usage.used, budget: usage.budget }
            )
          : intl.formatMessage(
              {
                id: "chat_context_gauge_tooltip",
                defaultMessage:
                  "Tokens of history used: {used, number} of {budget, number}. At 100%, the oldest messages stop being sent to the model and the figure drops to about 75%.",
              },
              { used: usage.used, budget: usage.budget }
            )}
      </TooltipContent>
    </Tooltip>
  )
}
