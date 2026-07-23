import Link from "next/link";
import { FolderTree } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/empty-state";
import { Progress } from "@/components/ui/progress";
import type { CategoryCount } from "@/features/dashboard/types";

export function CategoryDistribution({ byCategory }: { byCategory: CategoryCount[] }) {
  const max = Math.max(...byCategory.map((c) => c.documentCount), 1);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Documents by Category</CardTitle>
      </CardHeader>
      <CardContent>
        {byCategory.length === 0 ? (
          <EmptyState icon={FolderTree} title="No categories in use yet" />
        ) : (
          <div className="space-y-3">
            {byCategory.slice(0, 8).map((category) => (
              <Link
                key={category.categoryId}
                href={`/documents?categoryId=${category.categoryId}`}
                className="hover:bg-muted/60 focus-visible:ring-ring block rounded-lg px-2 py-1.5 outline-none focus-visible:ring-2"
              >
                <div className="flex items-center justify-between text-sm">
                  <span className="truncate font-medium">{category.categoryName}</span>
                  <span className="text-muted-foreground shrink-0 tabular-nums">{category.documentCount}</span>
                </div>
                <Progress value={(category.documentCount / max) * 100} className="mt-1.5" />
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
