"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api-client";
import { applyApiFieldErrors } from "@/lib/form-errors";
import { usePlatformLogin } from "@/features/platform/hooks";

const loginSchema = z.object({
  email: z.string().email("Enter a valid email address"),
  password: z.string().min(1, "Enter your password"),
});

type LoginValues = z.infer<typeof loginSchema>;

export function PlatformLoginForm() {
  const login = usePlatformLogin();

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  function onSubmit(values: LoginValues) {
    login.mutate(values, { onError: (error) => applyApiFieldErrors(form, error) });
  }

  const errorMessage = getErrorMessage(login.error);

  return (
    <div className="w-full max-w-sm space-y-8">
      <div className="space-y-1 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">DocBrain Platform</h1>
        <p className="text-muted-foreground text-sm">Manage organizations</p>
      </div>

      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <div className="space-y-1.5">
          <Label htmlFor="platform-email">Email</Label>
          <Input
            id="platform-email"
            type="email"
            autoComplete="email"
            placeholder="you@docbrain.dev"
            disabled={login.isPending}
            {...form.register("email")}
          />
          {form.formState.errors.email && (
            <p className="text-destructive text-xs">{form.formState.errors.email.message}</p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="platform-password">Password</Label>
          <Input
            id="platform-password"
            type="password"
            autoComplete="current-password"
            disabled={login.isPending}
            {...form.register("password")}
          />
          {form.formState.errors.password && (
            <p className="text-destructive text-xs">{form.formState.errors.password.message}</p>
          )}
        </div>

        {errorMessage && <p className="text-destructive text-sm">{errorMessage}</p>}

        <Button type="submit" className="w-full" disabled={login.isPending}>
          {login.isPending ? "Signing in…" : "Sign in"}
        </Button>
      </form>

      <p className="text-muted-foreground text-center text-xs">
        This is the internal platform console — not the regular DocBrain app.
      </p>
    </div>
  );
}

function getErrorMessage(error: unknown): string | null {
  if (!error) return null;
  if (error instanceof ApiError) {
    return error.status === 401 ? "That email and password don't match a platform admin account." : error.message;
  }
  return "Can't reach the server. Is the API running?";
}
