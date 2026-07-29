"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useCreateFirstAdmin } from "@/features/platform/hooks";
import { ApiError } from "@/lib/api-client";
import { applyApiFieldErrors } from "@/lib/form-errors";

const firstAdminSchema = z.object({
  email: z.string().email("Enter a valid email address"),
  displayName: z.string().min(1, "Name is required").max(200),
  password: z.string().min(8, "At least 8 characters"),
});

type FirstAdminValues = z.infer<typeof firstAdminSchema>;

interface CreateFirstAdminDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  organizationId: string;
  organizationName: string;
}

export function CreateFirstAdminDialog({
  open,
  onOpenChange,
  organizationId,
  organizationName,
}: CreateFirstAdminDialogProps) {
  const createFirstAdmin = useCreateFirstAdmin(organizationId);

  const form = useForm<FirstAdminValues>({
    resolver: zodResolver(firstAdminSchema),
    defaultValues: { email: "", displayName: "", password: "" },
  });

  function handleOpenChange(next: boolean) {
    if (createFirstAdmin.isPending) return;
    if (!next) form.reset();
    onOpenChange(next);
  }

  function onSubmit(values: FirstAdminValues) {
    createFirstAdmin.mutate(values, {
      onSuccess: (admin) => {
        toast.success(`${admin.displayName} can now sign in and invite the rest of ${organizationName}`);
        form.reset();
        onOpenChange(false);
      },
      onError: (error) => {
        if (applyApiFieldErrors(form, error)) return;
        toast.error(error instanceof ApiError ? error.message : "Couldn't create this admin, try again.");
      },
    });
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>First admin for {organizationName}</DialogTitle>
          <DialogDescription>
            This is the one account created directly rather than by invitation — there&apos;s no admin yet to send
            one.
            From here, this person invites everyone else at {organizationName}.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <fieldset disabled={createFirstAdmin.isPending} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="first-admin-name">Name</Label>
              <Input id="first-admin-name" {...form.register("displayName")} />
              {form.formState.errors.displayName && (
                <p className="text-destructive text-xs">{form.formState.errors.displayName.message}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="first-admin-email">Email</Label>
              <Input id="first-admin-email" type="email" {...form.register("email")} />
              {form.formState.errors.email && (
                <p className="text-destructive text-xs">{form.formState.errors.email.message}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="first-admin-password">Temporary password</Label>
              <Input id="first-admin-password" type="text" {...form.register("password")} />
              {form.formState.errors.password && (
                <p className="text-destructive text-xs">{form.formState.errors.password.message}</p>
              )}
              <p className="text-muted-foreground text-xs">Share this with them directly — it isn&apos;t emailed.</p>
            </div>
          </fieldset>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={createFirstAdmin.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createFirstAdmin.isPending}>
              {createFirstAdmin.isPending ? "Creating…" : "Create admin"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
