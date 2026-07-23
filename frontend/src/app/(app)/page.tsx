"use client";

import { AppBreadcrumb } from "@/components/layout/app-breadcrumb";
import { PageHeader } from "@/components/shared/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { useCurrentUser } from "@/features/auth/hooks";

export default function DashboardPage() {
  const { data: user, isLoading } = useCurrentUser();

  return (
    <div className="space-y-6">
      <AppBreadcrumb segments={[{ label: "Dashboard" }]} />
      <PageHeader
        title={isLoading ? "Loading…" : `Welcome back, ${user?.displayName.split(" ")[0]}`}
        description="The real dashboard widgets land in Phase 4.2 — this confirms the shell, auth guard, and API layer work end to end."
      />
      {isLoading ? (
        <Skeleton className="h-32 w-full rounded-lg" />
      ) : (
        <div className="text-muted-foreground rounded-lg border p-6 text-sm">
          Signed in as <span className="text-foreground font-medium">{user?.displayName}</span> ({user?.role})
        </div>
      )}
    </div>
  );
}
