"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { useAuth } from "@/hooks/use-auth";
import { stepUpPassword } from "@/lib/auth";
import { stepUpSchema } from "@/lib/schemas";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type StepUpFormValues = z.infer<typeof stepUpSchema>;

export function StepUpAuth({
  open,
  title,
  description,
  onOpenChange,
  onVerified,
}: {
  open: boolean;
  title: string;
  description: string;
  onOpenChange: (open: boolean) => void;
  onVerified: () => Promise<void> | void;
}) {
  const { user } = useAuth();
  const form = useForm<StepUpFormValues>({
    resolver: zodResolver(stepUpSchema),
    defaultValues: {
      password: "",
    },
  });

  const mutation = useMutation({
    mutationFn: async (values: StepUpFormValues) => {
      if (!user?.username) {
        throw new Error("Missing current user session.");
      }

      await stepUpPassword(user.username, values.password);
      await onVerified();
    },
    onSuccess: () => {
      toast.success("Identity confirmed.");
      form.reset();
      onOpenChange(false);
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Step-up verification failed.");
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md text-black">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-black">
            <ShieldCheck className="h-5 w-5 text-accent" />
            {title}
          </DialogTitle>
          <DialogDescription className="text-black">{description}</DialogDescription>
        </DialogHeader>
        <form
          className="space-y-4"
          onSubmit={form.handleSubmit((values) => {
            mutation.mutate(values);
          })}
        >
          <div className="space-y-2">
            <Label htmlFor="stepup-password">Password</Label>
            <Input id="stepup-password" type="password" {...form.register("password")} />
            {form.formState.errors.password ? (
              <p className="text-sm text-danger">{form.formState.errors.password.message}</p>
            ) : null}
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Confirming..." : "Confirm action"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
