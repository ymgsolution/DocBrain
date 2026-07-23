"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

// Root error boundary — catches render-time exceptions that fall through the
// query-level ErrorState handling scattered across pages (§16.5's 500 row:
// generic message + never a raw stack trace). Next.js requires this to be a
// Client Component and passes `error`/`reset` in.
export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-4 text-center">
      <div className="bg-destructive/10 mb-4 flex size-12 items-center justify-center rounded-full">
        <AlertTriangle className="text-destructive size-6" />
      </div>
      <h1 className="text-lg font-semibold">Something went wrong</h1>
      <p className="text-muted-foreground mt-1 max-w-sm text-sm">
        An unexpected error occurred. You can try again or head back to the Dashboard.
      </p>
      {error.digest && <p className="text-muted-foreground/70 mt-1 font-mono text-xs">Ref: {error.digest}</p>}
      <div className="mt-6 flex gap-2">
        <Button variant="outline" nativeButton={false} render={<Link href="/" />}>
          Go to Dashboard
        </Button>
        <Button onClick={() => reset()}>Retry</Button>
      </div>
    </div>
  );
}
