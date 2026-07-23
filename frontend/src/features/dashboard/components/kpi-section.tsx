import { ClipboardCheck, FileStack, FileText, FolderTree } from "lucide-react";
import { KpiCard } from "@/components/shared/kpi-card";
import { Skeleton } from "@/components/ui/skeleton";
import type { DashboardTotals } from "@/features/dashboard/types";

export function KpiSectionSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {Array.from({ length: 4 }, (_, i) => (
        <Skeleton key={i} className="h-24 rounded-xl" />
      ))}
    </div>
  );
}

export function KpiSection({ totals }: { totals: DashboardTotals }) {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <KpiCard icon={FileText} label="Total Documents" value={totals.totalDocuments} />
      <KpiCard icon={ClipboardCheck} label="Uploaded This Week" value={totals.uploadedThisWeek} />
      <KpiCard icon={FileStack} label="Versions Tracked" value={totals.versionsTracked} />
      <KpiCard icon={FolderTree} label="Categories In Use" value={totals.categoriesInUse} />
    </div>
  );
}
