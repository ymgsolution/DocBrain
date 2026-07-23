import { ShieldAlert } from "lucide-react";

export function ForbiddenState({ requiredRole }: { requiredRole: string }) {
  return (
    <div className="border-border bg-muted/30 flex flex-col items-center justify-center rounded-lg border py-16 text-center">
      <div className="bg-muted mb-4 flex size-12 items-center justify-center rounded-full">
        <ShieldAlert className="text-muted-foreground size-6" />
      </div>
      <h3 className="text-sm font-medium">You don&rsquo;t have permission to view this</h3>
      <p className="text-muted-foreground mt-1 max-w-sm text-sm">Requires the {requiredRole} role.</p>
    </div>
  );
}
