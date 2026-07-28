"use client";

import { useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { toast } from "sonner";
import { ShieldOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api-client";
import { publicAuthApi } from "@/features/auth/public-api";

const schema = z.object({
  displayName: z.string().min(2, "Enter your name"),
  // Mirrors the server's minimum. The server re-checks — this is only here
  // so the message arrives before a round trip.
  password: z.string().min(8, "Use at least 8 characters"),
});

type Values = z.infer<typeof schema>;

export function AcceptInviteForm({ token }: { token: string }) {
  const router = useRouter();

  const invitation = useQuery({
    queryKey: ["invitation", token],
    queryFn: () => publicAuthApi.getInvitation(token),
    // A dead invite is a permanent answer, not a blip worth hammering.
    retry: false,
  });

  const accept = useMutation({
    mutationFn: (values: Values) => publicAuthApi.acceptInvitation(token, values),
    onSuccess: () => {
      // Accepting deliberately doesn't create a session — the new user signs
      // in with the password they just chose, which proves it works and keeps
      // session creation on one well-tested path.
      toast.success("Account created — sign in with your new password");
      router.push("/login");
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Couldn't create your account, try again."),
  });

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { displayName: "", password: "" },
  });

  if (invitation.isLoading) {
    return <Skeleton className="h-56 w-full rounded-lg" />;
  }

  // One message for every failure — unknown, expired, revoked, already used —
  // matching the API, which deliberately doesn't distinguish them either.
  if (invitation.isError) {
    return (
      <div className="border-border flex flex-col items-center gap-3 rounded-xl border border-dashed py-12 text-center">
        <div className="bg-muted text-muted-foreground flex size-12 items-center justify-center rounded-full">
          <ShieldOff className="size-6" />
        </div>
        <div>
          <p className="text-sm font-medium">This invitation isn&apos;t available</p>
          <p className="text-muted-foreground mt-1 text-sm">
            It may have expired, been revoked, or already been used. Ask an administrator for a new one.
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-1 text-center">
        <p className="text-sm">
          You&apos;ve been invited as a{" "}
          <span className="font-medium capitalize">{invitation.data?.role.toLowerCase()}</span>
        </p>
        <p className="text-muted-foreground text-sm">{invitation.data?.email}</p>
      </div>

      <form
        onSubmit={form.handleSubmit((values) => accept.mutate(values))}
        className="space-y-4"
        noValidate
      >
        <div className="space-y-1.5">
          <Label htmlFor="displayName">Your name</Label>
          <Input
            id="displayName"
            autoComplete="name"
            placeholder="Jane Cooper"
            disabled={accept.isPending}
            {...form.register("displayName")}
          />
          {form.formState.errors.displayName && (
            <p className="text-destructive text-xs">{form.formState.errors.displayName.message}</p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="password">Choose a password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            disabled={accept.isPending}
            {...form.register("password")}
          />
          {form.formState.errors.password && (
            <p className="text-destructive text-xs">{form.formState.errors.password.message}</p>
          )}
        </div>

        <Button type="submit" className="w-full" disabled={accept.isPending}>
          {accept.isPending ? "Creating your account…" : "Create account"}
        </Button>
      </form>
    </>
  );
}
