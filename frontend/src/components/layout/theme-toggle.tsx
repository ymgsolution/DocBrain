"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useUpdatePreferences } from "@/features/auth/hooks";
import { ApiError } from "@/lib/api-client";
import type { ThemePreference } from "@/features/auth/types";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const updatePreferences = useUpdatePreferences();
  // Avoids a hydration mismatch: the resolved theme is only known client-side.
  // This is next-themes' own documented pattern for this exact problem — a
  // single one-time flag flip on mount, not a cascading-render risk.
  const [mounted, setMounted] = useState(false);
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setMounted(true), []);

  // Persists to the backend (fire-and-forget — the visual change from
  // setTheme is immediate and doesn't wait on the network) so the choice
  // survives to the next login, same control the Settings page uses.
  function handleSetTheme(value: ThemePreference) {
    setTheme(value);
    updatePreferences.mutate(
      { theme: value },
      {
        onError: (error) => {
          toast.error(error instanceof ApiError ? error.message : "Couldn't save your theme preference, try again.");
        },
      },
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={<Button variant="ghost" size="icon" aria-label="Toggle theme" />}>
        {mounted && theme === "dark" ? <Moon className="size-4" /> : <Sun className="size-4" />}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => handleSetTheme("light")}>
          <Sun className="size-4" />
          Light
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => handleSetTheme("dark")}>
          <Moon className="size-4" />
          Dark
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => handleSetTheme("system")}>
          <Monitor className="size-4" />
          System
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
