// Mirrors backend/app/core/config.py's Settings defaults — for instant
// client-side feedback only. The backend remains the real authority; these
// exist so a user sees "That file type isn't supported" immediately instead
// of after a round trip. Keep in sync if the backend defaults change.
export const ALLOWED_EXTENSIONS = [
  "pdf",
  "doc",
  "docx",
  "xls",
  "xlsx",
  "ppt",
  "pptx",
  "txt",
  "md",
  "csv",
  "png",
  "jpg",
];

export const MAX_UPLOAD_SIZE_MB = 25;
export const MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024;

export function getFileExtension(filename: string): string {
  return filename.includes(".") ? filename.split(".").pop()!.toLowerCase() : "";
}

export function validateUploadFile(file: File): string | null {
  const ext = getFileExtension(file.name);
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return `That file type isn't supported. Allowed types: ${ALLOWED_EXTENSIONS.join(", ")}.`;
  }
  if (file.size > MAX_UPLOAD_SIZE_BYTES) {
    return `File exceeds the ${MAX_UPLOAD_SIZE_MB} MB limit.`;
  }
  return null;
}
