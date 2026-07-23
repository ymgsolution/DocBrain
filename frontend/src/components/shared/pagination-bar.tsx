import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface PaginationBarProps {
  page: number; // 0-indexed
  size: number;
  total: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function PaginationBar({ page, size, total, totalPages, onPageChange }: PaginationBarProps) {
  if (total === 0) return null;

  const from = page * size + 1;
  const to = Math.min(total, (page + 1) * size);

  return (
    <div className="flex items-center justify-between gap-4 pt-1">
      <p className="text-muted-foreground text-sm">
        Showing <span className="text-foreground font-medium">{from}–{to}</span> of{" "}
        <span className="text-foreground font-medium">{total}</span>
      </p>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(page - 1)}
          disabled={page === 0}
          aria-label="Previous page"
        >
          <ChevronLeft className="size-4" />
          Previous
        </Button>
        <span className="text-muted-foreground text-sm tabular-nums">
          Page {page + 1} of {Math.max(totalPages, 1)}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(page + 1)}
          disabled={page + 1 >= totalPages}
          aria-label="Next page"
        >
          Next
          <ChevronRight className="size-4" />
        </Button>
      </div>
    </div>
  );
}
