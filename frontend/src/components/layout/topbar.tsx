"use client";

import { Menu, Plus, Search } from "lucide-react";
import { useState } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { SidebarContent } from "./sidebar";
import { ThemeToggle } from "./theme-toggle";
import { UserMenu } from "./user-menu";

// Lazy-loaded: the upload form/dropzone code only needs to reach the
// browser once someone actually opens it, not on every page load.
const UploadDocumentDialog = dynamic(
  () => import("@/features/documents/components/upload-document-dialog").then((m) => m.UploadDocumentDialog),
  { ssr: false },
);

export function Topbar() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [query, setQuery] = useState("");
  const router = useRouter();

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    router.push(`/documents?q=${encodeURIComponent(query.trim())}`);
  }

  return (
    <header className="border-border bg-background/95 supports-backdrop-filter:bg-background/80 sticky top-0 z-30 flex h-14 shrink-0 items-center gap-3 border-b px-4 backdrop-blur-sm">
      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        onClick={() => setMobileNavOpen(true)}
        aria-label="Open navigation"
      >
        <Menu className="size-5" />
      </Button>
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="w-60 p-0">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <SidebarContent onNavigate={() => setMobileNavOpen(false)} />
        </SheetContent>
      </Sheet>

      <form onSubmit={handleSearchSubmit} className="relative hidden max-w-sm flex-1 sm:block">
        <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2" />
        <Input
          placeholder="Search documents…"
          className="pl-8"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </form>

      <div className="flex flex-1 items-center justify-end gap-2">
        <Button size="sm" className="gap-1.5" onClick={() => setUploadOpen(true)}>
          <Plus className="size-4" />
          Upload
        </Button>
        <ThemeToggle />
        <UserMenu />
      </div>

      {uploadOpen && <UploadDocumentDialog open={uploadOpen} onOpenChange={setUploadOpen} />}
    </header>
  );
}
