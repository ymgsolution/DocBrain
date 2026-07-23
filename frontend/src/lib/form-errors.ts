import type { FieldValues, Path, UseFormReturn } from "react-hook-form";
import { ApiError } from "./api-client";

// Maps the backend's error envelope `fields[]` (§16.6 — present on both 422
// validation errors and field-specific 409 conflicts, e.g. a duplicate
// category name) onto react-hook-form field errors, so the same dialog that's
// already open shows exactly which field is wrong instead of just a toast.
// Returns true if at least one field error was applied, so the caller can
// skip showing a redundant generic toast on top.
export function applyApiFieldErrors<T extends FieldValues>(form: UseFormReturn<T>, error: unknown): boolean {
  if (!(error instanceof ApiError) || !error.fields?.length) return false;

  let applied = false;
  const knownFields = Object.keys(form.getValues());
  for (const { field, message } of error.fields) {
    if (knownFields.includes(field)) {
      form.setError(field as Path<T>, { type: "server", message });
      applied = true;
    }
  }
  return applied;
}
