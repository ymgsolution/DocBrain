import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";
import { DocumentListItem } from "@/components/shared/document-list-item";
import type { DocumentSummary } from "@/types/document";

interface DocumentListCardProps {
  title: string;
  icon: LucideIcon;
  documents: DocumentSummary[];
  emptyTitle: string;
  viewAllHref?: string;
  meta: (document: DocumentSummary) => string;
  trailing?: (document: DocumentSummary) => React.ReactNode;
}

export function DocumentListCard({
  title,
  icon,
  documents,
  emptyTitle,
  viewAllHref,
  meta,
  trailing,
}: DocumentListCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>{title}</CardTitle>
        {viewAllHref && documents.length > 0 && (
          <Button variant="ghost" size="sm" nativeButton={false} render={<Link href={viewAllHref} />}>
            View all
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {documents.length === 0 ? (
          <EmptyState icon={icon} title={emptyTitle} />
        ) : (
          <div className="space-y-1">
            {documents.map((document) => (
              <DocumentListItem
                key={document.id}
                document={document}
                meta={meta(document)}
                trailing={trailing?.(document)}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
