import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getVersionContentUrl } from "@/lib/api-client";

interface DownloadLinkProps {
  documentId: string;
  versionNumber: number;
  filename: string;
  variant?: "outline" | "ghost";
  size?: "sm" | "icon-sm";
}

export function DownloadLink({ documentId, versionNumber, filename, variant = "outline", size = "sm" }: DownloadLinkProps) {
  return (
    <Button
      variant={variant}
      size={size}
      nativeButton={false}
      render={
        <a
          href={getVersionContentUrl(documentId, versionNumber, "attachment")}
          download={filename}
          aria-label={size === "icon-sm" ? `Download ${filename}` : undefined}
        />
      }
    >
      <Download className="size-4" />
      {size !== "icon-sm" && "Download"}
    </Button>
  );
}
