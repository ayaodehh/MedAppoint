"use client";

import { useQuery } from "@tanstack/react-query";

import { RoleGate } from "@/components/auth/role-gate";
import { TopNav } from "@/components/layout/top-nav";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { apiClient, unwrapListResponse } from "@/lib/api-client";
import type { Appointment, PaginatedResponse } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

export default function PatientAppointmentsPage() {
  const appointmentsQuery = useQuery({
    queryKey: ["appointments", "mine"],
    queryFn: async () => unwrapListResponse(await apiClient.get<Appointment[] | PaginatedResponse<Appointment>>("/appointments/")),
  });

  return (
    <RoleGate allow={["patient"]}>
      <TopNav />
      <main className="page-shell py-10">
        <Card className="surface">
          <CardHeader>
            <CardTitle>My appointments</CardTitle>
            <CardDescription>Visit history and future appointment requests from the backend appointment service.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <THead>
                <TR>
                  <TH>Status</TH>
                  <TH>When</TH>
                  <TH>Reason</TH>
                  <TH>Notes</TH>
                </TR>
              </THead>
              <TBody>
                {appointmentsQuery.data?.map((appointment) => (
                  <TR key={appointment.id}>
                    <TD>
                      <Badge>{appointment.status}</Badge>
                    </TD>
                    <TD>{formatDateTime(appointment.scheduled_start)}</TD>
                    <TD>{appointment.reason}</TD>
                    <TD>{appointment.notes || "No notes"}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </CardContent>
        </Card>
      </main>
    </RoleGate>
  );
}
