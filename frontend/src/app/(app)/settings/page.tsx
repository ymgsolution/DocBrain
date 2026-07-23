"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useTheme } from "next-themes";
import { AppBreadcrumb } from "@/components/layout/app-breadcrumb";
import { PageHeader } from "@/components/shared/page-header";
import { UserAvatar } from "@/components/shared/user-avatar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useCurrentUser, usePreferences, useUpdatePreferences } from "@/features/auth/hooks";
import { ApiError } from "@/lib/api-client";
import type { ThemePreference } from "@/features/auth/types";

const THEME_LABELS: Record<ThemePreference, string> = {
  light: "Light",
  dark: "Dark",
  system: "System",
};

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

export default function SettingsPage() {
  const { data: user, isLoading: userLoading } = useCurrentUser();
  const { data: preferences, isLoading: preferencesLoading } = usePreferences();
  const updatePreferences = useUpdatePreferences();
  const { theme, setTheme } = useTheme();

  // next-themes resolves `theme` from localStorage synchronously on the
  // client's first render (a lazy useState initializer), which differs from
  // the server's SSR output — a real hydration mismatch, not just a FOUC
  // flash. Forcing "system" as the value until mounted keeps the Select's
  // value a string the whole time (never undefined, which Base UI treats as
  // uncontrolled) while still matching the server's render on first paint.
  const [mounted, setMounted] = useState(false);
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setMounted(true), []);

  function handleThemeChange(value: ThemePreference) {
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

  function handlePageSizeChange(value: number) {
    updatePreferences.mutate(
      { defaultPageSize: value },
      {
        onSuccess: () => toast.success("Default page size updated"),
        onError: (error) => {
          toast.error(error instanceof ApiError ? error.message : "Couldn't save this preference, try again.");
        },
      },
    );
  }

  return (
    <div className="max-w-2xl space-y-6">
      <AppBreadcrumb segments={[{ label: "Settings" }]} />
      <PageHeader title="Settings" description="Your profile and personal preferences." />

      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
        </CardHeader>
        <CardContent>
          {userLoading || !user ? (
            <Skeleton className="h-12 w-full rounded-lg" />
          ) : (
            <div className="flex items-center gap-3">
              <UserAvatar name={user.displayName} className="size-10" />
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{user.displayName}</p>
                <p className="text-muted-foreground truncate text-xs">{user.email}</p>
              </div>
              <Badge variant="outline" className="ml-auto font-normal capitalize">
                {user.role.toLowerCase()}
              </Badge>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Preferences</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <Label htmlFor="settings-theme">Theme</Label>
              <p className="text-muted-foreground text-xs">Applies immediately across the app.</p>
            </div>
            <Select
              value={mounted ? (theme ?? "system") : "system"}
              onValueChange={(value) => value && handleThemeChange(value as ThemePreference)}
            >
              <SelectTrigger id="settings-theme" className="w-36">
                <SelectValue placeholder="System">
                  {(value: ThemePreference) => THEME_LABELS[value] ?? "System"}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="light">Light</SelectItem>
                <SelectItem value="dark">Dark</SelectItem>
                <SelectItem value="system">System</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between gap-4">
            <div>
              <Label htmlFor="settings-page-size">Default page size</Label>
              <p className="text-muted-foreground text-xs">Used across document lists.</p>
            </div>
            {preferencesLoading || !preferences ? (
              <Skeleton className="h-8 w-36 rounded-lg" />
            ) : (
              <Select
                value={String(preferences.defaultPageSize)}
                onValueChange={(value) => value && handlePageSizeChange(Number(value))}
              >
                <SelectTrigger id="settings-page-size" className="w-36">
                  <SelectValue>{(value: string) => `${value} per page`}</SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {PAGE_SIZE_OPTIONS.map((size) => (
                    <SelectItem key={size} value={String(size)}>
                      {size} per page
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
