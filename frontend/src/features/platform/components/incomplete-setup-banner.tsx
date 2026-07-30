import { UserRoundX } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { OrganizationStats } from "@/features/platform/types";

/**
 * Creating an organization and creating its first admin are two separate
 * actions, and step one looks finished when it isn't: the dialog closes and
 * the organization appears in the table like any other. An organization with
 * no users can't be signed into and can't be invited into either (invitations
 * are sent by an admin, and there isn't one) — so stopping halfway leaves a
 * workspace nobody can reach, and there is no delete endpoint to undo it.
 * That happened for real; the organization sat unusable until it was removed
 * by hand.
 *
 * This makes the half-finished state visible instead of silent. It doesn't
 * prevent it — the two-step flow is deliberate, so an organization can be
 * created before deciding who runs it.
 */
export function IncompleteSetupBanner({ organizations }: { organizations: OrganizationStats[] }) {
  const incomplete = organizations.filter((org) => org.userCount === 0);
  if (incomplete.length === 0) return null;

  const isOne = incomplete.length === 1;

  return (
    <Card className="border-warning/30 bg-warning/5">
      <CardContent className="flex items-center gap-3">
        <div className="bg-warning/10 text-warning flex size-9 shrink-0 items-center justify-center rounded-lg">
          <UserRoundX className="size-4" />
        </div>
        <p className="text-sm">
          <span className="font-medium">
            {isOne ? incomplete[0].name : `${incomplete.length} organizations`}
          </span>{" "}
          {isOne ? "has" : "have"} no admin yet, so {isOne ? "it" : "they"} can&apos;t be signed into. Use{" "}
          <span className="font-medium">Create admin</span> to finish setting {isOne ? "it" : "them"} up.
        </p>
      </CardContent>
    </Card>
  );
}
