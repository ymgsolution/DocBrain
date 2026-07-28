"use client";

import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api-client";
import { publicAuthApi } from "@/features/auth/public-api";

const schema = z.object({ password: z.string().min(8, "Use at least 8 characters") });
type Values = z.infer<typeof schema>;

export function ResetPasswordForm({ token }: { token: string }) {
  const router = useRouter();

  const reset = useMutation({
    mutationFn: (values: Values) => publicAuthApi.confirmPasswordReset(token, values.password),
    onSuccess: () => {
      // No session is created here either — the user signs in with what they
      // just set, keeping session creation on the single login path.
      toast.success("Password updated — sign in with your new password");
      router.push("/login");
    },
    onError: (error) =>
      toast.error(
        error instanceof ApiError && error.status === 404
          ? "This reset link is invalid, has expired, or has already been used."
          : "Couldn't update your password, try again.",
      ),
  });

  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { password: "" } });

  return (
    <>
      <div className="space-y-1 text-center">
        <p className="text-sm font-medium">Set a new password</p>
        <p className="text-muted-foreground text-sm">Choose something you haven&apos;t used before.</p>
      </div>

      <form onSubmit={form.handleSubmit((values) => reset.mutate(values))} className="space-y-4" noValidate>
        <div className="space-y-1.5">
          <Label htmlFor="password">New password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            disabled={reset.isPending}
            {...form.register("password")}
          />
          {form.formState.errors.password && (
            <p className="text-destructive text-xs">{form.formState.errors.password.message}</p>
          )}
        </div>
        <Button type="submit" className="w-full" disabled={reset.isPending}>
          {reset.isPending ? "Updating…" : "Update password"}
        </Button>
      </form>
    </>
  );
}
