"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Check, Copy, Mail, UserPlus } from "lucide-react";
import { AppBreadcrumb } from "@/components/layout/app-breadcrumb";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { ForbiddenState } from "@/components/shared/forbidden-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ApiError } from "@/lib/api-client";
import { useCurrentUser } from "@/features/auth/hooks";
import { useInvitations, useCreateInvitation, useRevokeInvitation } from "@/features/invitations/hooks";
import type { InvitationCreated, InvitationStatus } from "@/types/invitation";
import type { UserRole } from "@/types/api";

const ROLES: { value: UserRole; label: string }[] = [
  { value: "EMPLOYEE", label: "Employee" },
  { value: "REVIEWER", label: "Reviewer" },
  { value: "ADMIN", label: "Admin" },
];

const STATUS_VARIANT: Record<InvitationStatus, "outline" | "secondary"> = {
  pending: "outline",
  accepted: "secondary",
  revoked: "secondary",
  expired: "secondary",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export default function InvitationsAdminPage() {
  const { data: user, isLoading: userLoading } = useCurrentUser();
  const { data: invitations, isLoading, isError, error, refetch } = useInvitations();
  const createInvite = useCreateInvitation();
  const revokeInvite = useRevokeInvitation();

  const [email, setEmail] = useState("");
  const [role, setRole] = useState<UserRole>("EMPLOYEE");
  // Held in state, not refetched: the raw token exists only in the create
  // response, so once this is dismissed the link genuinely cannot be shown
  // again — the admin must revoke and re-invite.
  const [justCreated, setJustCreated] = useState<InvitationCreated | null>(null);
  const [copied, setCopied] = useState(false);

  if (userLoading) return <Skeleton className="h-64 w-full rounded-lg" />;

  if (user && user.role !== "ADMIN") {
    return (
      <div className="space-y-6">
        <AppBreadcrumb segments={[{ label: "Invitations" }]} />
        <ForbiddenState requiredRole="Admin" />
      </div>
    );
  }

  function handleInvite() {
    createInvite.mutate(
      { email: email.trim(), role, expiresInDays: 7 },
      {
        onSuccess: (invitation) => {
          setJustCreated(invitation);
          setCopied(false);
          setEmail("");
          toast.success(`Invitation sent to ${invitation.email}`);
        },
        onError: (err) =>
          toast.error(err instanceof ApiError ? err.message : "Couldn't create that invitation."),
      },
    );
  }

  async function handleCopy() {
    if (!justCreated) return;
    try {
      await navigator.clipboard.writeText(justCreated.url);
      setCopied(true);
      toast.success("Invite link copied");
    } catch {
      toast.error("Couldn't copy automatically — select the link and copy it.");
    }
  }

  function handleRevoke(id: string, invitedEmail: string) {
    revokeInvite.mutate(id, {
      onSuccess: () => {
        if (justCreated?.id === id) setJustCreated(null);
        toast.success(`Invitation for ${invitedEmail} revoked`);
      },
      onError: (err) =>
        toast.error(err instanceof ApiError ? err.message : "Couldn't revoke that invitation."),
    });
  }

  return (
    <div className="space-y-6">
      <AppBreadcrumb segments={[{ label: "Invitations" }]} />
      <PageHeader
        title="Invitations"
        description="Accounts are invite-only. Invite someone by email, or send them the link yourself."
      />

      <div className="border-border bg-muted/30 space-y-4 rounded-xl border p-4">
        <div className="grid gap-3 sm:grid-cols-[1fr_auto_auto] sm:items-end">
          <div className="space-y-1.5">
            <Label htmlFor="invite-email">Email</Label>
            <Input
              id="invite-email"
              type="email"
              placeholder="new.person@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={createInvite.isPending}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="invite-role">Role</Label>
            <Select value={role} onValueChange={(value) => value && setRole(value as UserRole)}>
              <SelectTrigger id="invite-role" className="w-full sm:w-40">
                <SelectValue>{ROLES.find((r) => r.value === role)?.label}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {ROLES.map((r) => (
                  <SelectItem key={r.value} value={r.value}>
                    {r.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button onClick={handleInvite} disabled={!email.trim() || createInvite.isPending}>
            <UserPlus className="size-4" />
            {createInvite.isPending ? "Inviting…" : "Send invite"}
          </Button>
        </div>

        {justCreated && (
          <div className="space-y-2 border-t pt-4">
            <Label htmlFor="invite-url">
              {/* Explicit {" "}: JSX drops the space between an expression and
                  the text that follows it on the same line, which ran the
                  email straight into the dash. */}
              Invite link for {justCreated.email}{" "}
              <span className="text-muted-foreground">— copy it now, it won&apos;t be shown again</span>
            </Label>
            <div className="flex gap-2">
              <Input id="invite-url" readOnly value={justCreated.url} onFocus={(e) => e.target.select()} />
              <Button type="button" variant="outline" onClick={handleCopy} aria-label="Copy invite link">
                {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
              </Button>
            </div>
            <p className="text-muted-foreground flex items-center gap-1.5 text-xs">
              <Mail className="size-3.5" />
              We&apos;ve emailed this link too — sharing it yourself works just as well.
            </p>
          </div>
        )}
      </div>

      {isLoading ? (
        <Skeleton className="h-64 w-full rounded-lg" />
      ) : isError ? (
        <ErrorState
          message={error instanceof ApiError ? error.message : "Couldn't load invitations."}
          correlationId={error instanceof ApiError ? error.correlationId : undefined}
          onRetry={() => refetch()}
        />
      ) : !invitations?.length ? (
        <EmptyState
          icon={UserPlus}
          title="No invitations yet"
          description="Invite someone above to give them access to this workspace."
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[34%]">Email</TableHead>
              <TableHead className="w-[14%]">Role</TableHead>
              <TableHead className="w-[14%]">Status</TableHead>
              <TableHead className="w-[18%]">Expires</TableHead>
              <TableHead className="w-[20%] text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {invitations.map((invitation) => (
              <TableRow key={invitation.id}>
                <TableCell className="truncate font-medium">{invitation.email}</TableCell>
                <TableCell className="capitalize">{invitation.role.toLowerCase()}</TableCell>
                <TableCell>
                  <Badge variant={STATUS_VARIANT[invitation.status]} className="capitalize">
                    {invitation.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">{formatDate(invitation.expiresAt)}</TableCell>
                <TableCell className="text-right">
                  {invitation.status === "pending" && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleRevoke(invitation.id, invitation.email)}
                      disabled={revokeInvite.isPending}
                    >
                      Revoke
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
