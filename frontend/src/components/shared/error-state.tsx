import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  title?: string;
  message?: string;
  correlationId?: string;
  onRetry?: () => void;
}

export function ErrorState({ title = "Something went wrong", message, correlationId, onRetry }: ErrorStateProps) {
  return (
    <div className="border-destructive/30 bg-destructive/5 flex flex-col items-center justify-center rounded-lg border py-16 text-center">
      <div className="bg-destructive/10 mb-4 flex size-12 items-center justify-center rounded-full">
        <AlertTriangle className="text-destructive size-6" />
      </div>
      <h3 className="text-sm font-medium">{title}</h3>
      {message && <p className="text-muted-foreground mt-1 max-w-sm text-sm">{message}</p>}
      {correlationId && <p className="text-muted-foreground/70 mt-1 font-mono text-xs">Ref: {correlationId}</p>}
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-4" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}
