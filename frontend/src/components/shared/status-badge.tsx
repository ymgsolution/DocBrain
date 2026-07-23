import { AlertCircle, CheckCircle2, Clock } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type ReviewStatus = "ok" | "due_soon" | "overdue";

const REVIEW_STATUS_CONFIG: Record<ReviewStatus, { label: string; icon: LucideIcon; className: string }> = {
  ok: {
    label: "Up to date",
    icon: CheckCircle2,
    className: "bg-success/10 text-success border-success/20",
  },
  due_soon: {
    label: "Due soon",
    icon: Clock,
    className: "bg-warning/10 text-warning border-warning/30",
  },
  overdue: {
    label: "Overdue",
    icon: AlertCircle,
    className: "bg-destructive/10 text-destructive border-destructive/20",
  },
};

// Status is never communicated by colour alone (accessibility rule, §5.7) —
// every variant pairs its colour with a distinct icon and label.
export function ReviewStatusBadge({ status, className }: { status: ReviewStatus; className?: string }) {
  const config = REVIEW_STATUS_CONFIG[status];
  const Icon = config.icon;
  return (
    <Badge variant="outline" className={cn("gap-1 font-normal", config.className, className)}>
      <Icon className="size-3" />
      {config.label}
    </Badge>
  );
}
