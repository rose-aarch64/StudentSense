import { intl } from "@/i18n/intl"

import type { LogEntry } from "./api"
import { canvasCodeText } from "./canvas-error-text"

function text(entry: LogEntry, key: string): string {
  return String(entry.params[key] ?? "")
}

function count(entry: LogEntry, key: string): number {
  return Number(entry.params[key] ?? 0)
}

/** One log line in the user's words, or null for a code this release does not know. */
export function canvasLogText(entry: LogEntry): string | null {
  switch (entry.code) {
    case "sync_started":
      return intl.formatMessage({
        id: "canvas_log_sync_started_status",
        defaultMessage: "Sync started",
      })
    case "check_started":
      return intl.formatMessage({
        id: "canvas_log_check_started_status",
        defaultMessage: "Check started",
      })
    case "class_started":
      return intl.formatMessage(
        {
          id: "canvas_log_class_started_status",
          defaultMessage: "Reading {name}…",
        },
        { name: text(entry, "name") }
      )
    case "class_read":
      return intl.formatMessage(
        {
          id: "canvas_log_class_read_status",
          defaultMessage:
            "Read {assignments, plural, one {# assignment} other {# assignments}}, {announcements, plural, one {# announcement} other {# announcements}}, {modules, plural, one {# module} other {# modules}}, {pages, plural, one {# page} other {# pages}} and {files, plural, one {# file} other {# files}}.",
        },
        {
          assignments: count(entry, "assignments"),
          announcements: count(entry, "announcements"),
          modules: count(entry, "modules"),
          pages: count(entry, "pages"),
          files: count(entry, "files"),
        }
      )
    case "pages_tab_off":
      return intl.formatMessage(
        {
          id: "canvas_log_pages_tab_off_status",
          defaultMessage:
            "The Pages tab is off for {name}, so its pages are read through its modules.",
        },
        { name: text(entry, "name") }
      )
    case "file_kept":
      return intl.formatMessage(
        { id: "canvas_log_file_kept_status", defaultMessage: "Kept {name}" },
        { name: text(entry, "name") }
      )
    case "file_updated":
      return intl.formatMessage(
        {
          id: "canvas_log_file_updated_status",
          defaultMessage: "Updated {name}",
        },
        { name: text(entry, "name") }
      )
    case "file_skipped":
      return intl.formatMessage(
        {
          id: "canvas_log_file_skipped_status",
          defaultMessage:
            "Skipped {name}: SurfSense cannot read it, or already holds it.",
        },
        { name: text(entry, "name") }
      )
    case "file_failed":
      return intl.formatMessage(
        {
          id: "canvas_log_file_failed_error",
          defaultMessage: "Could not fetch {name}.",
        },
        { name: text(entry, "name") }
      )
    case "class_checked":
      return intl.formatMessage(
        {
          id: "canvas_log_class_checked_status",
          defaultMessage:
            "{name}: {changed, plural, one {# file changed in Canvas} other {# files changed in Canvas}}, {gone, plural, one {# no longer listed} other {# no longer listed}}.",
        },
        {
          name: text(entry, "name"),
          changed: count(entry, "changed"),
          gone: count(entry, "gone"),
        }
      )
    case "finished":
      return intl.formatMessage(
        {
          id: "canvas_log_finished_status",
          defaultMessage:
            "Done: {classes, plural, one {# class} other {# classes}}, {errors, plural, =0 {no errors} one {# error} other {# errors}}.",
        },
        { classes: count(entry, "classes"), errors: count(entry, "errors") }
      )
    case "stopped":
      return intl.formatMessage(
        { id: "canvas_log_stopped_error", defaultMessage: "Stopped: {reason}" },
        { reason: canvasCodeText(text(entry, "error")) }
      )
    default:
      return null
  }
}
