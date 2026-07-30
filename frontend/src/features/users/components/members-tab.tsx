"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Users } from "lucide-react";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { PaginationBar } from "@/components/shared/pagination-bar";
import { SearchBox } from "@/components/shared/search-box";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { ApiError } from "@/lib/api-client";
import { useCurrentUser } from "@/features/auth/hooks";
import {
  useAdminUsers,
  useChangeUserRole,
  useDeactivateUser,
  useReactivateUser,
} from "@/features/users/hooks";
import type { AdminUser, UserStatusFilter } from "@/types/user-admin";
import type { UserRole } from "@/types/api";

const PAGE_SIZE = 25;

const ROLES: { value: UserRole; label: string }[] = [
  { value: "EMPLOYEE", label: "Employee" },
  { value: "REVIEWER", label: "Reviewer" },
  { value: "ADMIN", label: "Admin" },
];

const STATUSES: { value: UserStatusFilter; label: string }[] = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Deactivated" },
  { value: "all", label: "All" },
];

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function errorText(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function MembersTab() {
  const { data: currentUser } = useCurrentUser();

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<UserStatusFilter>("active");
  const [page, setPage] = useState(0);
  const [pendingDeactivation, setPendingDeactivation] = useState<AdminUser | null>(null);

  const { data, isLoading, isError, error, refetch } = useAdminUsers({
    search: search || undefined,
    status,
    page,
    size: PAGE_SIZE,
  });

  const deactivate = useDeactivateUser();
  const reactivate = useReactivateUser();
  const changeRole = useChangeUserRole();

  function handleSearch(value: string) {
    setSearch(value);
    // Page 3 of the old result set is meaningless against a new filter, and
    // lands on an empty table that reads as "no results".
    setPage(0);
  }

  function handleStatus(value: UserStatusFilter) {
    setStatus(value);
    setPage(0);
  }

  function handleDeactivate() {
    const target = pendingDeactivation;
    if (!target) return;
    deactivate.mutate(target.id, {
      onSuccess: () => {
        setPendingDeactivation(null);
        toast.success(`${target.displayName} has been deactivated`);
      },
      onError: (err) => toast.error(errorText(err, "Couldn't deactivate that account.")),
    });
  }

  function handleReactivate(user: AdminUser) {
    reactivate.mutate(user.id, {
      onSuccess: () => toast.success(`${user.displayName} can sign in again`),
      onError: (err) => toast.error(errorText(err, "Couldn't reactivate that account.")),
    });
  }

  function handleRoleChange(user: AdminUser, role: UserRole) {
    changeRole.mutate(
      { id: user.id, role },
      {
        onSuccess: () => toast.success(`${user.displayName} is now ${role.toLowerCase()}`),
        onError: (err) => toast.error(errorText(err, "Couldn't change that role.")),
      },
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <SearchBox
          placeholder="Search by name or email…"
          onValueChange={handleSearch}
          className="sm:max-w-sm"
        />
        <Select value={status} onValueChange={(value) => value && handleStatus(value as UserStatusFilter)}>
          <SelectTrigger className="w-full sm:w-44">
            <SelectValue>{STATUSES.find((s) => s.value === status)?.label}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            {STATUSES.map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <Skeleton className="h-64 w-full rounded-lg" />
      ) : isError ? (
        <ErrorState
          message={errorText(error, "Couldn't load people.")}
          correlationId={error instanceof ApiError ? error.correlationId : undefined}
          onRetry={() => refetch()}
        />
      ) : !data?.items.length ? (
        <EmptyState
          icon={Users}
          title={search ? "No one matches that search" : "No one here yet"}
          description={
            search
              ? "Try a different name or email, or widen the status filter."
              : "Invite someone from the Invitations tab to get started."
          }
        />
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[30%]">Name</TableHead>
                <TableHead className="w-[16%]">Role</TableHead>
                <TableHead className="w-[16%]">Status</TableHead>
                <TableHead className="w-[16%]">Joined</TableHead>
                <TableHead className="w-[22%] text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((user) => {
                const isSelf = user.id === currentUser?.id;
                return (
                  <TableRow key={user.id} className={user.isActive ? undefined : "opacity-60"}>
                    <TableCell>
                      <div className="font-medium">
                        {user.displayName}
                        {isSelf && <span className="text-muted-foreground font-normal"> (you)</span>}
                      </div>
                      <div className="text-muted-foreground truncate text-xs">{user.email}</div>
                    </TableCell>

                    <TableCell>
                      {isSelf ? (
                        // Changing your own role is refused by the API — it
                        // would 403 you out of this very page — so it isn't
                        // offered here either.
                        <Tooltip>
                          <TooltipTrigger
                            render={<span tabIndex={0} className="text-muted-foreground text-sm capitalize" />}
                          >
                            {user.role.toLowerCase()}
                          </TooltipTrigger>
                          <TooltipContent>You can&apos;t change your own role</TooltipContent>
                        </Tooltip>
                      ) : (
                        <Select
                          value={user.role}
                          onValueChange={(value) =>
                            value && value !== user.role && handleRoleChange(user, value as UserRole)
                          }
                          disabled={changeRole.isPending || !user.isActive}
                        >
                          <SelectTrigger size="sm" className="w-32">
                            <SelectValue>{ROLES.find((r) => r.value === user.role)?.label}</SelectValue>
                          </SelectTrigger>
                          <SelectContent>
                            {ROLES.map((r) => (
                              <SelectItem key={r.value} value={r.value}>
                                {r.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    </TableCell>

                    <TableCell>
                      {user.isActive ? (
                        <Badge variant="outline">Active</Badge>
                      ) : (
                        <Tooltip>
                          <TooltipTrigger render={<span tabIndex={0} />}>
                            <Badge variant="secondary">Deactivated</Badge>
                          </TooltipTrigger>
                          <TooltipContent>
                            {user.deactivatedAt
                              ? `By ${user.deactivatedBy?.displayName ?? "an administrator"} on ${formatDate(user.deactivatedAt)}`
                              : "This account can't sign in"}
                          </TooltipContent>
                        </Tooltip>
                      )}
                    </TableCell>

                    <TableCell className="text-muted-foreground">{formatDate(user.createdAt)}</TableCell>

                    <TableCell className="text-right">
                      {isSelf ? (
                        <Tooltip>
                          <TooltipTrigger
                            render={<span tabIndex={0} className="text-muted-foreground text-xs" />}
                          >
                            —
                          </TooltipTrigger>
                          <TooltipContent>
                            Ask another admin to deactivate your account
                          </TooltipContent>
                        </Tooltip>
                      ) : user.isActive ? (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setPendingDeactivation(user)}
                          disabled={deactivate.isPending}
                        >
                          Deactivate
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleReactivate(user)}
                          disabled={reactivate.isPending}
                        >
                          Reactivate
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>

          <PaginationBar
            page={data.page}
            size={data.size}
            total={data.total}
            totalPages={data.totalPages}
            onPageChange={setPage}
          />
        </>
      )}

      <ConfirmDialog
        open={pendingDeactivation !== null}
        onOpenChange={(open) => !open && setPendingDeactivation(null)}
        title={`Deactivate ${pendingDeactivation?.displayName ?? ""}?`}
        // Spells out both halves: what stops (immediately, not at logout) and
        // what survives, because "deactivate" reads as "delete" to most people.
        description={
          `They'll be signed out straight away and won't be able to sign back in. Any share links they created will stop working. ` +
          `Their documents, versions and history stay exactly as they are, and you can reactivate them at any time.`
        }
        confirmLabel="Deactivate"
        destructive
        loading={deactivate.isPending}
        onConfirm={handleDeactivate}
      />
    </div>
  );
}
