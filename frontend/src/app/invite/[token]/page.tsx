import type { Metadata } from "next";
import { AuthShell } from "@/features/auth/components/auth-shell";
import { AcceptInviteForm } from "@/features/auth/components/accept-invite-form";

// Outside the (app) route group: the person opening this has no account
// yet, so there is no workspace shell to render. See proxy.ts, where
// /invite/ is matched as a shared path so it opens with or without a session.
export const metadata: Metadata = {
  title: "Accept your invitation · DocBrain",
  robots: { index: false, follow: false },
};

export default async function AcceptInvitePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return (
    <AuthShell>
      <AcceptInviteForm token={token} />
    </AuthShell>
  );
}
