"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarCheck2, ReceiptText } from "lucide-react";
import { toast } from "sonner";

import { RoleGate } from "@/components/auth/role-gate";
import { StepUpAuth } from "@/components/auth/step-up-auth";
import { TopNav } from "@/components/layout/top-nav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { apiClient, unwrapListResponse } from "@/lib/api-client";
import type { Appointment, PaginatedResponse } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

export default function ReceptionAppointmentsPage() {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<Appointment | null>(null);
  const [dueAt, setDueAt] = useState("");

  const appointmentsQuery = useQuery({
    queryKey: ["staff", "appointments"],
    queryFn: async () => unwrapListResponse(await apiClient.get<Appointment[] | PaginatedResponse<Appointment>>("/appointments/")),
  });

  const closeAndBillMutation = useMutation({
    mutationFn: async (appointment: Appointment) => {
      await apiClient.post(`/appointments/${appointment.id}/set_status/`, { status: "completed" });
      const invoice = await apiClient.post<{ id: number }>(
        "/billing/invoices/",
        {
          patient: appointment.patient,
          appointment: appointment.id,
          currency: "USD",
          status: "pending",
          due_at: dueAt || null,
        },
      );
      await apiClient.post(`/billing/invoices/${invoice.id}/charge/`, {});
    },
    onSuccess: () => {
      toast.success("Appointment closed and billed.");
      setSelected(null);
      queryClient.invalidateQueries({ queryKey: ["staff", "appointments"] });
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Could not close and bill.");
    },
  });

  return (
    <RoleGate allow={["admin", "receptionist", "billing"]}>
      <TopNav staff />
      <main className="page-shell py-10">
        <section className="mb-6 grid gap-4 lg:grid-cols-2">
          <Card className="surface">
            <CardHeader>
              <ReceiptText className="h-8 w-8 text-accent" />
              <CardTitle>Billing source of truth</CardTitle>
              <CardDescription>
                Invoice amounts now come from the linked appointment on the server. Frontend staff can only set timing, not price.
              </CardDescription>
            </CardHeader>
          </Card>
          <Card className="surface bg-panel text-paper">
            <CardHeader>
              <CalendarCheck2 className="h-8 w-8 text-accent-soft" />
              <CardTitle className="text-paper">Reception workflow</CardTitle>
              <CardDescription className="text-paper/80">
                Confirm visit details, optionally set a due date, then complete the appointment and let billing compute the charge.
              </CardDescription>
            </CardHeader>
          </Card>
        </section>
        <Card className="surface">
          <CardHeader>
            <CardTitle>Reception appointments</CardTitle>
            <CardDescription>Review schedule requests and trigger close-and-bill for a completed visit.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <THead>
                <TR>
                  <TH>Status</TH>
                  <TH>Patient</TH>
                  <TH>Start</TH>
                  <TH>Reason</TH>
                  <TH>Invoice amount</TH>
                  <TH>Due at</TH>
                  <TH>Action</TH>
                </TR>
              </THead>
              <TBody>
                {appointmentsQuery.data?.map((appointment) => (
                  <TR key={appointment.id}>
                    <TD>
                      <Badge>{appointment.status}</Badge>
                    </TD>
                    <TD>{appointment.patient}</TD>
                    <TD>{formatDateTime(appointment.scheduled_start)}</TD>
                    <TD>{appointment.reason}</TD>
                    <TD>
                      <Badge className="bg-accent-soft text-accent-strong">Server computed</Badge>
                    </TD>
                    <TD>
                      <input
                        className="flex h-11 w-full min-w-40 rounded-2xl border border-line bg-paper px-4 py-2 text-sm text-ink outline-none transition placeholder:text-ink-muted/70 focus:border-accent"
                        id={`due-${appointment.id}`}
                        type="datetime-local"
                        value={selected?.id === appointment.id ? dueAt : ""}
                        onChange={(event) => {
                          setSelected(appointment);
                          setDueAt(event.target.value);
                        }}
                      />
                    </TD>
                    <TD>
                      <Button
                        variant="danger"
                        onClick={() => {
                          setSelected(appointment);
                        }}
                      >
                        Close and bill
                      </Button>
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </CardContent>
        </Card>
        <StepUpAuth
          open={Boolean(selected)}
          title="Step-up required"
          description="Billing is a sensitive action. Re-enter your password before the invoice is created and charged."
          onOpenChange={(open) => {
            if (!open) {
              setSelected(null);
            }
          }}
          onVerified={async () => {
            if (!selected) {
              return;
            }
            await closeAndBillMutation.mutateAsync(selected);
          }}
        />
      </main>
    </RoleGate>
  );
}
