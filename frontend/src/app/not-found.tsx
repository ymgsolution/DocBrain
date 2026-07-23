import Link from "next/link";
import { FileQuestion } from "lucide-react";
import { Button } from "@/components/ui/button";

// Router-level 404 — an unmatched route, not a per-page "this document was
// deleted" state (those are handled per-screen, e.g. documents/[id]/page.tsx).
// §16.5's 404 row applies here too: this used to fall through to Next's
// default unstyled 404 with no way back into the app.
export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-4 text-center">
      <div className="bg-muted mb-4 flex size-12 items-center justify-center rounded-full">
        <FileQuestion className="text-muted-foreground size-6" />
      </div>
      <h1 className="text-lg font-semibold">We couldn&rsquo;t find that page</h1>
      <p className="text-muted-foreground mt-1 max-w-sm text-sm">
        The page you&rsquo;re looking for doesn&rsquo;t exist or may have moved.
      </p>
      <Button className="mt-6" nativeButton={false} render={<Link href="/" />}>
        Go to Dashboard
      </Button>
    </div>
  );
}
