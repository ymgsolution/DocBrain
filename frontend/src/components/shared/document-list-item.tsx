import Link from "next/link";
import { FileTypeIcon } from "@/components/shared/file-type-icon";
import type { DocumentSummary } from "@/types/document";

interface DocumentListItemProps {
  document: DocumentSummary;
  meta: string;
  trailing?: React.ReactNode;
}

export function DocumentListItem({ document, meta, trailing }: DocumentListItemProps) {
  return (
    <Link
      href={`/documents/${document.id}`}
      className="hover:bg-muted/60 focus-visible:ring-ring flex items-center gap-3 rounded-lg px-2 py-2 outline-none focus-visible:ring-2"
    >
      <div className="bg-muted text-muted-foreground flex size-8 shrink-0 items-center justify-center rounded-md">
        <FileTypeIcon filename={document.currentVersion?.originalFilename ?? document.title} className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{document.title}</p>
        <p className="text-muted-foreground truncate text-xs">{meta}</p>
      </div>
      {trailing && <div className="shrink-0">{trailing}</div>}
    </Link>
  );
}
