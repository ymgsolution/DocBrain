import { FileText } from "lucide-react";

/** The frame shared by every signed-out page (invite, reset, forgot).
 *  Deliberately minimal — someone who isn't in the workspace shouldn't see
 *  its navigation, and these pages render outside the (app) layout anyway. */
export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-8">
        <div className="space-y-1 text-center">
          <div className="flex items-center justify-center gap-2">
            <FileText className="text-primary size-5" />
            <span className="text-2xl font-semibold tracking-tight">DocBrain</span>
          </div>
        </div>
        {children}
      </div>
    </main>
  );
}
