"use client";

import Link from "next/link";
import { ShieldAlert } from "lucide-react";

import { useAuth } from "@/hooks/use-auth";
import type { Role } from "@/lib/types";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function RoleGate({
  allow,
  children,
  fallback,
}: {
  allow: Role[];
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const { user, isLoading, error } = useAuth();

  if (isLoading) {
    return (
      <main className="page-shell py-16">
        <Card className="surface mx-auto max-w-xl">
          <CardHeader>
            <CardTitle>Checking your session</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-ink-muted">
            Loading your account and permissions.
          </CardContent>
        </Card>
      </main>
    );
  }

  if (error) {
    return (
      <main className="page-shell py-16">
        <Card className="surface mx-auto max-w-xl">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-danger">
              <ShieldAlert className="h-5 w-5" />
              Session unavailable
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-ink-muted">
            <p>We could not verify your session with the server. This usually means the backend API is not reachable.</p>
            <Button asChild variant="accent">
              <Link href="/login">Return to login</Link>
            </Button>
          </CardContent>
        </Card>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="page-shell py-16">
        <Card className="surface mx-auto max-w-xl">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-danger">
              <ShieldAlert className="h-5 w-5" />
              Sign-in required
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-ink-muted">
            <p>Your session is missing or expired. Sign in again to continue.</p>
            <Button asChild variant="accent">
              <Link href="/login">Go to login</Link>
            </Button>
          </CardContent>
        </Card>
      </main>
    );
  }

  if (!allow.includes(user.role)) {
    return (
      fallback ?? (
        <Card className="surface">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-danger">
              <ShieldAlert className="h-5 w-5" />
              Access restricted
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-ink-muted">
            Your account does not have permission to view this section.
          </CardContent>
        </Card>
      )
    );
  }

  return <>{children}</>;
}
