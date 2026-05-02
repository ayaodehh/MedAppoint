"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { CalendarClock, FolderHeart, ReceiptText, type LucideIcon } from "lucide-react";

import { RoleGate } from "@/components/auth/role-gate";
import { TopNav } from "@/components/layout/top-nav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient, unwrapListResponse } from "@/lib/api-client";
import type { Appointment, Invoice, PaginatedResponse, Patient } from "@/lib/types";
import { formatCurrency, formatDateTime } from "@/lib/utils";

const UPCOMING_STATUSES: ReadonlyArray<Appointment["status"]> = ["requested", "confirmed"];

export default function PatientDashboardPage() {
  const patientQuery = useQuery({
    queryKey: ["patients", "mine"],
    queryFn: async () => {
      const result = await apiClient.get<Patient[] | PaginatedResponse<Patient>>("/patients/");
      return unwrapListResponse(result)[0] ?? null;
    },
  });

  const appointmentsQuery = useQuery({
    queryKey: ["appointments", "mine"],
    queryFn: async () => unwrapListResponse(await apiClient.get<Appointment[] | PaginatedResponse<Appointment>>("/appointments/")),
  });

  const invoicesQuery = useQuery({
    queryKey: ["invoices", "mine"],
    queryFn: async () => unwrapListResponse(await apiClient.get<Invoice[] | PaginatedResponse<Invoice>>("/billing/invoices/")),
  });

  const nextAppointment = useMemo(() => {
    const list = appointmentsQuery.data;
    if (!list) return null;
    const now = Date.now();
    return (
      list
        .filter((appointment) => UPCOMING_STATUSES.includes(appointment.status))
        .filter((appointment) => new Date(appointment.scheduled_start).getTime() >= now)
        .sort((a, b) => new Date(a.scheduled_start).getTime() - new Date(b.scheduled_start).getTime())[0] ?? null
    );
  }, [appointmentsQuery.data]);

  const balanceDue = useMemo(() => {
    if (!invoicesQuery.data?.length) return 0;
    return invoicesQuery.data
      .filter((invoice) => invoice.status !== "paid" && invoice.status !== "void")
      .reduce((sum, invoice) => {
        const amount = Number(invoice.amount_due);
        return sum + (Number.isFinite(amount) ? amount : 0);
      }, 0);
  }, [invoicesQuery.data]);

  const isLoading = patientQuery.isPending || appointmentsQuery.isPending || invoicesQuery.isPending;
  const loadError = patientQuery.error ?? appointmentsQuery.error ?? invoicesQuery.error;

  const upcomingValue = appointmentsQuery.isPending
    ? "Loading…"
    : appointmentsQuery.isError
      ? "Unavailable"
      : nextAppointment
        ? formatDateTime(nextAppointment.scheduled_start)
        : "None";

  const mrnValue = patientQuery.isPending
    ? "Loading…"
    : patientQuery.isError
      ? "Unavailable"
      : patientQuery.data?.medical_record_number ?? "Pending";

  const balanceValue = invoicesQuery.isPending
    ? "Loading…"
    : invoicesQuery.isError
      ? "Unavailable"
      : formatCurrency(balanceDue);

  return (
    <RoleGate allow={["patient"]}>
      <TopNav />
      <main className="page-shell py-10">
        {loadError ? (
          <div
            role="alert"
            className="mb-6 rounded-[20px] border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800"
          >
            We couldn&apos;t load some of your dashboard data. Please refresh the page or try again shortly.
          </div>
        ) : null}
        <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]" aria-busy={isLoading}>
          <Card className="surface">
            <CardHeader>
              <Badge>Patient dashboard</Badge>
              <CardTitle>
                {patientQuery.isPending
                  ? "Loading your profile…"
                  : patientQuery.data?.full_name ?? "Your clinic profile"}
              </CardTitle>
              <CardDescription>See upcoming appointments, billing state, and identity-linked record details.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-3">
              <MetricCard icon={CalendarClock} label="Upcoming" value={upcomingValue} />
              <MetricCard icon={FolderHeart} label="MRN" value={mrnValue} />
              <MetricCard icon={ReceiptText} label="Balance" value={balanceValue} />
            </CardContent>
          </Card>
          <Card className="surface bg-panel text-paper">
            <CardHeader>
              <CardTitle className="text-paper">Next steps</CardTitle>
              <CardDescription className="text-paper/75">Use the patient workflow pages in the order most people need them.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button asChild variant="accent" className="w-full justify-between">
                <Link href="/book">Book appointment</Link>
              </Button>
              <Button asChild variant="outline" className="w-full justify-between border-paper/20 bg-transparent text-paper hover:bg-paper/10">
                <Link href="/appointments">Review my appointments</Link>
              </Button>
            </CardContent>
          </Card>
        </section>
      </main>
    </RoleGate>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-[24px] border border-line bg-paper-strong p-4">
      <div className="flex items-center justify-between">
        <p className="text-sm uppercase tracking-[0.18em] text-ink-muted">{label}</p>
        <Icon className="h-5 w-5 text-accent" />
      </div>
      <p className="mt-4 text-xl font-semibold text-panel">{value}</p>
    </div>
  );
}
