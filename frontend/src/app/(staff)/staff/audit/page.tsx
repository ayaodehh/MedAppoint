"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";

import { RoleGate } from "@/components/auth/role-gate";
import { StepUpAuth } from "@/components/auth/step-up-auth";
import { TopNav } from "@/components/layout/top-nav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { apiClient, unwrapListResponse } from "@/lib/api-client";
import type { AuditLogEntry, PaginatedResponse } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

export default function AuditLogPage() {
  const [stepUpOpen, setStepUpOpen] = useState(false);
  const auditQuery = useQuery({
    queryKey: ["staff", "audit"],
    queryFn: async () => unwrapListResponse(await apiClient.get<AuditLogEntry[] | PaginatedResponse<AuditLogEntry>>("/audit/logs/")),
  });

  const adminRefreshMutation = useMutation({
    mutationFn: async () => {
      await auditQuery.refetch();
    },
    onSuccess: () => {
      toast.success("Audit log refreshed.");
    },
  });

  return (
    <RoleGate allow={["admin", "auditor"]}>
      <TopNav staff />
      <main className="page-shell py-10">
        <Card className="surface">
          <CardHeader className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <CardTitle>Audit log viewer</CardTitle>
              <CardDescription>Read-only backend audit events for logins, updates, billing, and EHR operations.</CardDescription>
            </div>
            <Button variant="danger" onClick={() => setStepUpOpen(true)}>
              Refresh with step-up
            </Button>
          </CardHeader>
          <CardContent>
            <Table>
              <THead>
                <TR>
                  <TH>Status</TH>
                  <TH>Action</TH>
                  <TH>Resource</TH>
                  <TH>When</TH>
                  <TH>IP</TH>
                </TR>
              </THead>
              <TBody>
                {auditQuery.data?.map((entry) => (
                  <TR key={entry.id}>
                    <TD>
                      <Badge className={entry.status === "failure" ? "bg-red-100 text-danger" : undefined}>{entry.status}</Badge>
                    </TD>
                    <TD>{entry.action}</TD>
                    <TD>
                      {entry.resource_type || "auth"}:{entry.resource_id || "-"}
                    </TD>
                    <TD>{formatDateTime(entry.created_at)}</TD>
                    <TD>{entry.ip_address ?? "n/a"}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </CardContent>
        </Card>
        <StepUpAuth
          open={stepUpOpen}
          title="Step-up required"
          description="Refreshing or reviewing sensitive administrative data requires fresh password confirmation."
          onOpenChange={setStepUpOpen}
          onVerified={async () => {
            await adminRefreshMutation.mutateAsync();
          }}
        />
      </main>
    </RoleGate>
  );
}
