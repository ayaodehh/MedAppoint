import Link from "next/link";
import { ArrowRight, CalendarHeart, ShieldCheck, Stethoscope } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function Hero() {
  return (
    <main className="page-shell py-12 md:py-20">
      <section className="grid gap-8 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <div className="surface grid-stripes rounded-[36px] border border-line p-8 md:p-12">
          <p className="mb-4 text-xs font-semibold uppercase tracking-[0.3em] text-accent-strong">Patient experience</p>
          <h1 className="max-w-3xl font-serif text-5xl leading-tight text-panel md:text-7xl">
            Book visits, follow care plans, and keep the paperwork out of the waiting room.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-ink-muted">
            This portal talks to the Django clinic backend using secure HTTP-only cookie sessions, patient-safe route guards,
            and explicit role-based access for staff workflows.
          </p>
          <div className="mt-8 flex flex-wrap gap-4">
            <Button asChild variant="accent" size="lg">
              <Link href="/register">
                Create patient account
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link href="/login">Patient login</Link>
            </Button>
            <Button asChild variant="ghost" size="lg">
              <Link href="/staff/login">Staff access</Link>
            </Button>
          </div>
        </div>
        <div className="grid gap-6 md:grid-cols-3 xl:grid-cols-1">
          <Card className="surface">
            <CardHeader>
              <CalendarHeart className="h-10 w-10 text-accent" />
              <CardTitle>Smart booking flow</CardTitle>
              <CardDescription>Patients can register, authenticate, and request appointments from one place.</CardDescription>
            </CardHeader>
          </Card>
          <Card className="surface bg-panel text-black">
            <CardHeader>
              <ShieldCheck className="h-10 w-10 text-accent-soft" />
              <CardTitle className="text-black">Step-up security</CardTitle>
              <CardDescription className="text-black/80">
                Sensitive billing and admin actions require a fresh password confirmation before submission.
              </CardDescription>
            </CardHeader>
          </Card>
          <Card className="surface">
            <CardHeader>
              <Stethoscope className="h-10 w-10 text-warning" />
              <CardTitle>Staff split by role</CardTitle>
              <CardDescription>Reception, clinicians, billing staff, and auditors only see what they are allowed to use.</CardDescription>
            </CardHeader>
          </Card>
        </div>
      </section>
    </main>
  );
}
