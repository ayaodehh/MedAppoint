"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
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

type LoginFormValues = z.infer<typeof loginSchema>;

export default function PatientLoginPage() {
  const router = useRouter();
  const { user, isLoading, login } = useAuth();
  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      username: "",
      password: "",
      otp_token: "",
    },
  });

  useEffect(() => {
    if (!isLoading && user?.role === "patient") {
      router.replace("/dashboard");
    }
  }, [isLoading, router, user]);

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await login.mutateAsync(values);
      toast.success("Welcome back.");
      router.replace("/dashboard");
      router.refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Login failed.");
    }
  });

  return (
    <main className="page-shell py-16">
      <Card className="surface mx-auto max-w-xl">
        <CardHeader>
          <CardTitle>Patient login</CardTitle>
          <CardDescription>Use your clinic account. The browser sends secure cookies automatically.</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-5"
            onSubmit={onSubmit}
          >
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input id="username" {...form.register("username")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" {...form.register("password")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="otp_token">OTP token</Label>
              <Input id="otp_token" placeholder="Optional unless OTP is enabled" {...form.register("otp_token")} />
            </div>
            <Button type="submit" variant="accent" className="w-full" disabled={login.isPending}>
              {login.isPending ? "Signing in..." : "Sign in"}
            </Button>
            <p className="text-sm text-ink-muted">
              Need an account?{" "}
              <Link className="font-semibold text-accent-strong" href="/register">
                Register here
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
