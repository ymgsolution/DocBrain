"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AppBreadcrumb } from "@/components/layout/app-breadcrumb";
import { PageHeader } from "@/components/shared/page-header";
import { ForbiddenState } from "@/components/shared/forbidden-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCurrentUser } from "@/features/auth/hooks";
import { InvitationsTab } from "@/features/invitations/components/invitations-tab";
import { MembersTab } from "@/features/users/components/members-tab";

const TABS = ["members", "invitations"] as const;
type Tab = (typeof TABS)[number];

// useSearchParams opts the subtree out of static prerendering, so it has to
// sit under a Suspense boundary or the production build fails. The boundary
// lives here rather than around the whole page so the header still renders
// immediately.
export default function PeopleAdminPage() {
  return (
    <Suspense fallback={<Skeleton className="h-64 w-full rounded-lg" />}>
      <PeopleAdmin />
    </Suspense>
  );
}

function PeopleAdmin() {
  const { data: user, isLoading } = useCurrentUser();
  const router = useRouter();
  const searchParams = useSearchParams();

  // Tab lives in the URL so /admin/people?tab=invitations is linkable and
  // survives a refresh — which also lets the old /admin/invitations route
  // redirect straight to the right tab instead of a generic landing.
  const requested = searchParams.get("tab");
  const tab: Tab = TABS.includes(requested as Tab) ? (requested as Tab) : "members";

  function handleTabChange(next: string) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", next);
    router.replace(`/admin/people?${params.toString()}`, { scroll: false });
  }

  if (isLoading) return <Skeleton className="h-64 w-full rounded-lg" />;

  if (user && user.role !== "ADMIN") {
    return (
      <div className="space-y-6">
        <AppBreadcrumb segments={[{ label: "People" }]} />
        <ForbiddenState requiredRole="Admin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <AppBreadcrumb segments={[{ label: "People" }]} />
      <PageHeader
        title="People"
        description="Everyone with access to this workspace, and the invitations that let them in."
      />

      <Tabs value={tab} onValueChange={handleTabChange}>
        <TabsList>
          <TabsTrigger value="members">Members</TabsTrigger>
          <TabsTrigger value="invitations">Invitations</TabsTrigger>
        </TabsList>

        <TabsContent value="members" className="mt-4">
          <MembersTab />
        </TabsContent>

        <TabsContent value="invitations" className="mt-4">
          <InvitationsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
