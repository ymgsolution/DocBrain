import type { ExtractionStatus, ReviewStatus } from "@/types/document";

export function getInitials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

const RELATIVE_UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 60 * 60 * 24 * 365],
  ["month", 60 * 60 * 24 * 30],
  ["week", 60 * 60 * 24 * 7],
  ["day", 60 * 60 * 24],
  ["hour", 60 * 60],
  ["minute", 60],
];

const relativeTimeFormatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

export function formatRelativeTime(isoDate: string): string {
  const seconds = (new Date(isoDate).getTime() - Date.now()) / 1000;
  for (const [unit, secondsInUnit] of RELATIVE_UNITS) {
    if (Math.abs(seconds) >= secondsInUnit) {
      return relativeTimeFormatter.format(Math.round(seconds / secondsInUnit), unit);
    }
  }
  return relativeTimeFormatter.format(Math.round(seconds / 60), "minute");
}

// Mirrors the backend's exact thresholds (documents/repository.py) so a
// document never shows a different status client-side than it would filter
// to in the Explorer's reviewStatus=… query param.
export function getReviewStatus(reviewDueDate: string | null): ReviewStatus {
  if (!reviewDueDate) return "ok";
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(reviewDueDate);
  const horizonMs = 30 * 24 * 60 * 60 * 1000;
  if (due.getTime() < today.getTime()) return "overdue";
  if (due.getTime() <= today.getTime() + horizonMs) return "due_soon";
  return "ok";
}

// AI feature track — 2 minutes: parsing is fast, so if a version's
// extraction hasn't resolved by then, the worker is probably down or the job
// is stuck. Shared by the badge (whether to render) and useDocument's
// refetchInterval (whether to keep polling), so they can never disagree —
// no case where polling silently stops but the spinner is still shown, or
// vice versa. Keyed off the version's own uploadedAt, not "now minus mount
// time" or the document's updatedAt (which also moves on unrelated edits) —
// a backfilled document uploaded long ago should never show this badge, even
// while its one-time catch-up job is genuinely in flight; the badge's job is
// "something is happening for what you just uploaded," not "surface every
// background job's state."
const EXTRACTION_TIMEOUT_MS = 2 * 60 * 1000;

export function isExtractionPending(document: {
  extractionStatus: ExtractionStatus;
  currentVersion: { uploadedAt: string } | null;
}): boolean {
  const unresolved = document.extractionStatus === null || document.extractionStatus === "PENDING";
  if (!unresolved || !document.currentVersion) return false;
  const elapsed = Date.now() - new Date(document.currentVersion.uploadedAt).getTime();
  return elapsed < EXTRACTION_TIMEOUT_MS;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex++;
  }
  return `${value.toFixed(value < 10 ? 1 : 0)} ${units[unitIndex]}`;
}
