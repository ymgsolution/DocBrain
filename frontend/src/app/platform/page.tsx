"use client";

import { useState } from "react";
import { Building2, LogOut, Plus, UserPlus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { CreateFirstAdminDialog } from "@/features/platform/components/create-first-admin-dialog";
import { CreateOrganizationDialog } from "@/features/platform/components/create-organization-dialog";
import { IncompleteSetupBanner } from "@/features/platform/components/incomplete-setup-banner";
import { useCurrentPlatformAdmin, useOrganizations, usePlatformLogout } from "@/features/platform/hooks";
import { formatRelativeTime } from "@/lib/format";
import type { OrganizationStats } from "@/features/platform/types";

export default function PlatformDashboardPage() {
  const { data: admin } = useCurrentPlatformAdmin();
  const { data: organizations, isLoading, isError, refetch } = useOrganizations();
  const logout = usePlatformLogout();

  const [createOrgOpen, setCreateOrgOpen] = useState(false);
  const [adminTarget, setAdminTarget] = useState<OrganizationStats | null>(null);

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="bg-primary text-primary-foreground flex size-7 items-center justify-center rounded-md">
            <Building2 className="size-4" />
          </div>
          <span className="text-sm font-semibold">DocBrain Platform</span>
        </div>
        <div className="flex items-center gap-3">
          {admin && <span className="text-muted-foreground text-sm">{admin.email}</span>}
          <Button variant="ghost" size="sm" className="gap-1.5" onClick={() => logout.mutate()}>
            <LogOut className="size-4" />
            Sign out
          </Button>
        </div>
      </div>

      <PageHeader
        title="Organizations"
        description="Every company workspace on DocBrain — counts only, never document content."
        actions={
          <Button size="sm" className="gap-1.5" onClick={() => setCreateOrgOpen(true)}>
            <Plus className="size-4" />
            Create Organization
          </Button>
        }
      />

      {isLoading && <Skeleton className="h-64 w-full rounded-lg" />}

      {isError && <ErrorState message="Couldn't load organizations." onRetry={() => refetch()} />}

      {organizations && <IncompleteSetupBanner organizations={organizations} />}

      {organizations && organizations.length === 0 && (
        <EmptyState
          icon={Building2}
          title="No organizations yet"
          description="Create the first one to get started."
          action={
            <Button size="sm" className="gap-1.5" onClick={() => setCreateOrgOpen(true)}>
              <Plus className="size-4" />
              Create Organization
            </Button>
          }
        />
      )}

      {organizations && organizations.length > 0 && (
        <div className="border-border overflow-hidden rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Organization</TableHead>
                <TableHead>Users</TableHead>
                <TableHead>Documents</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {organizations.map((org) => {
                // No users at all means nobody can sign in and nobody can be
                // invited either, since invitations come from an admin — the
                // organization is unreachable until one exists.
                const needsAdmin = org.userCount === 0;
                return (
                  <TableRow key={org.id}>
                    <TableCell className="font-medium">
                      {org.name}
                      <span className="text-muted-foreground ml-2 text-xs">{org.slug}</span>
                    </TableCell>
                    <TableCell>
                      {needsAdmin ? (
                        <Badge variant="destructive">No admin</Badge>
                      ) : (
                        <>
                          {org.userCount}
                          <Badge variant="secondary" className="ml-2">
                            {org.activeUserCount} active
                          </Badge>
                        </>
                      )}
                    </TableCell>
                    <TableCell>{org.documentCount}</TableCell>
                    <TableCell className="text-muted-foreground">{formatRelativeTime(org.createdAt)}</TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant={needsAdmin ? "default" : "outline"}
                        size="sm"
                        className="gap-1.5"
                        onClick={() => setAdminTarget(org)}
                      >
                        <UserPlus className="size-4" />
                        {needsAdmin ? "Create admin" : "Add admin"}
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      <CreateOrganizationDialog open={createOrgOpen} onOpenChange={setCreateOrgOpen} />

      {adminTarget && (
        <CreateFirstAdminDialog
          open={Boolean(adminTarget)}
          onOpenChange={(open) => !open && setAdminTarget(null)}
          organizationId={adminTarget.id}
          organizationName={adminTarget.name}
        />
      )}
    </div>
  );
}
