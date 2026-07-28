"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api-client";
import { applyApiFieldErrors } from "@/lib/form-errors";
import { useLogin } from "@/features/auth/hooks";

const loginSchema = z.object({
  email: z.string().email("Enter a valid email address"),
  // Length/complexity rules belong on the *set password* form, not here.
  // Telling someone their attempt is "too short" to sign in only reveals
  // what the stored password isn't.
  password: z.string().min(1, "Enter your password"),
});

type LoginValues = z.infer<typeof loginSchema>;

export function LoginForm() {
  const login = useLogin();

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
        <h1 className="text-2xl font-semibold tracking-tight">DocBrain</h1>
        <p className="text-muted-foreground text-sm">Sign in to continue</p>
      </div>

      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@company.com"
            disabled={login.isPending}
            {...form.register("email")}
          />
          {form.formState.errors.email && (
            <p className="text-destructive text-xs">{form.formState.errors.email.message}</p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
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
        Accounts are created by invitation — ask an administrator for access.
      </p>
    </div>
  );
}

function getErrorMessage(error: unknown): string | null {
  if (!error) return null;
  if (error instanceof ApiError) {
    // Deliberately one message for every 401, mirroring the API: naming
    // which half was wrong would let someone probe for valid addresses.
    return error.status === 401 ? "That email and password don't match an account." : error.message;
  }
  return "Can't reach the server. Is the API running?";
}
