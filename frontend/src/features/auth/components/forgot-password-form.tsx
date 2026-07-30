"use client";

import Link from "next/link";
import { useMutation } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { MailCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { publicAuthApi } from "@/features/auth/public-api";

const schema = z.object({ email: z.string().email("Enter a valid email address") });
type Values = z.infer<typeof schema>;

export function ForgotPasswordForm() {
  const request = useMutation({
    mutationFn: (values: Values) => publicAuthApi.requestPasswordReset(values.email),
  });

  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { email: "" } });

  // Shown whether or not the address exists, mirroring the API's deliberate
  // 202-for-everything. Confirming "no such account" here would undo the
  // server-side work to stop this being an account-enumeration tool.
  if (request.isSuccess) {
    return (
      <div className="border-border flex flex-col items-center gap-3 rounded-xl border border-dashed py-12 text-center">
        <div className="bg-muted text-muted-foreground flex size-12 items-center justify-center rounded-full">
          <MailCheck className="size-6" />
        </div>
        <div>
          <p className="text-sm font-medium">Check your email</p>
          <p className="text-muted-foreground mt-1 text-sm">
            If that address has an account, a reset link is on its way. It expires in 30 minutes.
          </p>
        </div>
        <Link href="/login" className="text-primary text-sm underline-offset-4 hover:underline">
          Back to sign in
        </Link>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-1 text-center">
        <p className="text-sm font-medium">Forgot your password?</p>
        <p className="text-muted-foreground text-sm">
          Enter your email and we&apos;ll send you a link to set a new one.
        </p>
      </div>

      <form
        onSubmit={form.handleSubmit((values) => request.mutate(values))}
        className="space-y-4"
        noValidate
      >
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@company.com"
            disabled={request.isPending}
            {...form.register("email")}
          />
          {form.formState.errors.email && (
            <p className="text-destructive text-xs">{form.formState.errors.email.message}</p>
          )}
        </div>

        <Button type="submit" className="w-full" disabled={request.isPending}>
          {request.isPending ? "Sending…" : "Send reset link"}
        </Button>
        <p className="text-center">
          <Link href="/login" className="text-muted-foreground text-xs underline-offset-4 hover:underline">
            Back to sign in
          </Link>
        </p>
      </form>
    </>
  );
}
