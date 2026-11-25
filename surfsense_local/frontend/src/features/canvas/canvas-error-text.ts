import { ApiError } from "@/lib/api"
import { intl } from "@/i18n/intl"

/** What went wrong talking to Canvas, in the user's words. */
export function canvasErrorText(error: unknown): string {
  return canvasCodeText(error instanceof ApiError ? error.code : null)
}

/** The same words for an error code the backend recorded, such as a failed refresh. */
export function canvasCodeText(code: string | null): string {
  switch (code) {
    case "canvas_token_refused":
      return intl.formatMessage({
        id: "canvas_error_token_refused",
        defaultMessage: "Canvas did not accept that token.",
      })
    case "canvas_needs_https":
      return intl.formatMessage({
        id: "canvas_error_needs_https",
        defaultMessage: "Canvas must be reached over https.",
      })
    case "canvas_bad_address":
      return intl.formatMessage({
        id: "canvas_error_bad_address",
        defaultMessage: "That is not a web address.",
      })
    case "canvas_unreachable":
      return intl.formatMessage({
        id: "canvas_error_unreachable",
        defaultMessage: "Canvas could not be reached.",
      })
    case "canvas_token_unreadable":
      return intl.formatMessage({
        id: "canvas_error_token_unreadable",
        defaultMessage:
          "The saved token cannot be read on this computer. Connect Canvas again.",
      })
    case "egress_disabled":
      return intl.formatMessage({
        id: "canvas_error_egress_disabled",
        defaultMessage: "Canvas is switched off in Settings › Network.",
      })
    case "embedding_not_chosen":
      return intl.formatMessage({
        id: "canvas_error_embedding_not_chosen",
        defaultMessage: "Choose an embedding model first, then sync.",
      })
    default:
      return intl.formatMessage({
        id: "canvas_error_generic",
        defaultMessage: "Something went wrong talking to Canvas.",
      })
  }
}
