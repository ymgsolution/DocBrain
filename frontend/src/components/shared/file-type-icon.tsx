import { File as FileIcon, FileImage, FileSpreadsheet, FileText, Presentation } from "lucide-react";
import type { LucideIcon } from "lucide-react";

const EXTENSION_ICON: Record<string, LucideIcon> = {
  pdf: FileText,
  doc: FileText,
  docx: FileText,
  txt: FileText,
  md: FileText,
  xls: FileSpreadsheet,
  xlsx: FileSpreadsheet,
  csv: FileSpreadsheet,
  ppt: Presentation,
  pptx: Presentation,
  png: FileImage,
  jpg: FileImage,
  jpeg: FileImage,
};

export function FileTypeIcon({ filename, className }: { filename: string; className?: string }) {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  const Icon = EXTENSION_ICON[ext] ?? FileIcon;
  return <Icon className={className} />;
}
