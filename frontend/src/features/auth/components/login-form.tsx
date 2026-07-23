"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api-client";
import { getInitials } from "@/lib/format";
import { usePersonas, useLogin } from "@/features/auth/hooks";

const loginSchema = z.object({
  email: z.string().email("Enter a valid email address"),
});

type LoginValues = z.infer<typeof loginSchema>;

export function LoginForm() {
  const { data: personas, isLoading: personasLoading } = usePersonas();
  const login = useLogin();

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "" },
  });

  function onSubmit(values: LoginValues) {
    login.mutate({ email: values.email });
  }

  const errorMessage = getErrorMessage(login.error);

  return (
    <div className="w-full max-w-sm space-y-8">
      <div className="space-y-1 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">DocBrain</h1>
        <p className="text-muted-foreground text-sm">Sign in to continue</p>
      </div>

      <div className="grid gap-2">
        {personasLoading &&
          Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 rounded-lg" />)}
        {personas?.map((persona) => (
          <button
            key={persona.id}
            type="button"
            disabled={login.isPending}
            onClick={() => login.mutate({ email: persona.email })}
            className="border-border hover:bg-accent hover:border-primary/30 focus-visible:ring-ring flex items-center gap-3 rounded-lg border p-3 text-left transition-colors focus-visible:ring-2 focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50"
          >
            <Avatar>
              <AvatarFallback className="bg-primary/10 text-primary text-sm font-medium">
                {getInitials(persona.displayName)}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{persona.displayName}</p>
              <p className="text-muted-foreground text-xs capitalize">{persona.role.toLowerCase()}</p>
            </div>
          </button>
        ))}
      </div>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="border-border w-full border-t" />
        </div>
        <div className="relative flex justify-center text-xs">
          <span className="bg-background text-muted-foreground px-2">or sign in with email</span>
        </div>
      </div>

      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-3" noValidate>
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
        {errorMessage && <p className="text-destructive text-sm">{errorMessage}</p>}
        <Button type="submit" className="w-full" disabled={login.isPending}>
          {login.isPending ? "Signing in…" : "Sign in"}
        </Button>
      </form>

      <p className="text-muted-foreground text-center text-xs">Mock authentication — Phase 1</p>
    </div>
  );
}

function getErrorMessage(error: unknown): string | null {
  if (!error) return null;
  if (error instanceof ApiError) {
    return error.status === 401 ? "No account matches that email — pick a demo user below." : error.message;
  }
  return "Can't reach the server. Is the API running?";
}
