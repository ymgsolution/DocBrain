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
import { useCreateOrganization } from "@/features/platform/hooks";
import { ApiError } from "@/lib/api-client";
import { applyApiFieldErrors } from "@/lib/form-errors";

const organizationSchema = z.object({
  name: z.string().min(1, "Name is required").max(200),
});

type OrganizationValues = z.infer<typeof organizationSchema>;

interface CreateOrganizationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateOrganizationDialog({ open, onOpenChange }: CreateOrganizationDialogProps) {
  const createOrganization = useCreateOrganization();

  const form = useForm<OrganizationValues>({
    resolver: zodResolver(organizationSchema),
    defaultValues: { name: "" },
  });

  function handleOpenChange(next: boolean) {
    if (createOrganization.isPending) return;
    if (!next) form.reset();
    onOpenChange(next);
  }

  function onSubmit(values: OrganizationValues) {
    createOrganization.mutate(values, {
      onSuccess: (org) => {
        toast.success(`"${org.name}" created`);
        form.reset();
        onOpenChange(false);
      },
      onError: (error) => {
        if (applyApiFieldErrors(form, error)) return;
        toast.error(error instanceof ApiError ? error.message : "Couldn't create this organization, try again.");
      },
    });
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New organization</DialogTitle>
          <DialogDescription>
            Creates an empty workspace. Add its first admin next, from the organization&apos;s row.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <fieldset disabled={createOrganization.isPending} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="org-name">Company name</Label>
              <Input id="org-name" placeholder="e.g. Infosys" {...form.register("name")} />
              {form.formState.errors.name && (
                <p className="text-destructive text-xs">{form.formState.errors.name.message}</p>
              )}
            </div>
          </fieldset>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={createOrganization.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createOrganization.isPending}>
              {createOrganization.isPending ? "Creating…" : "Create organization"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
