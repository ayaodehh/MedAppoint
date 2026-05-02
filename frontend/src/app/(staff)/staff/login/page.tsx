"use client";

import { useEffect } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { useAuth } from "@/hooks/use-auth";
import { loginSchema } from "@/lib/schemas";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type StaffLoginFormValues = z.infer<typeof loginSchema>;

function getPostLoginRoute(role: string) {
  if (role === "patient") {
    return "/dashboard";
  }
  if (role === "admin" || role === "auditor") {
    return "/staff/audit";
  }
  if (role === "clinician") {
    return "/staff/schedule";
  }
  return "/staff/appointments";
}

export default function StaffLoginPage() {
  const { user, isLoading, login } = useAuth();
  const form = useForm<StaffLoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      username: "",
      password: "",
      otp_token: "",
    },
  });

  useEffect(() => {
    if (!isLoading && user?.role) {
      window.location.replace(getPostLoginRoute(user.role));
    }
  }, [isLoading, user]);

  return (
    <main className="page-shell py-16">
      <Card className="surface mx-auto max-w-xl">
        <CardHeader>
          <CardTitle>Staff login</CardTitle>
          <CardDescription>Reception, clinician, billing, and audit users authenticate here.</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-5"
            onSubmit={form.handleSubmit(async (values) => {
              try {
                const authenticatedUser = await login.mutateAsync(values);
                toast.success("Staff session ready.");
                window.location.replace(getPostLoginRoute(authenticatedUser.role));
              } catch (error) {
                toast.error(error instanceof Error ? error.message : "Login failed.");
              }
            })}
          >
            <div className="space-y-2">
              <Label htmlFor="staff-username">Username</Label>
              <Input id="staff-username" {...form.register("username")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="staff-password">Password</Label>
              <Input id="staff-password" type="password" {...form.register("password")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="staff-otp">OTP token</Label>
              <Input id="staff-otp" {...form.register("otp_token")} />
            </div>
            <Button type="submit" variant="accent" className="w-full" disabled={login.isPending}>
              {login.isPending ? "Signing in..." : "Enter staff workspace"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
