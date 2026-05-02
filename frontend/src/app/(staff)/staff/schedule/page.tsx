"use client";

import { useMemo } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm, type UseFormRegisterReturn } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { RoleGate } from "@/components/auth/role-gate";
import { TopNav } from "@/components/layout/top-nav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { clinicalNoteSchema } from "@/lib/schemas";
import { apiClient, unwrapListResponse } from "@/lib/api-client";
import type { Appointment, PaginatedResponse, Patient } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

type ClinicalNoteValues = z.infer<typeof clinicalNoteSchema>;

export default function DoctorSchedulePage() {
  const queryClient = useQueryClient();
  const appointmentsQuery = useQuery({
    queryKey: ["staff", "doctor", "appointments"],
    queryFn: async () => unwrapListResponse(await apiClient.get<Appointment[] | PaginatedResponse<Appointment>>("/appointments/")),
  });
  const patientsQuery = useQuery({
    queryKey: ["staff", "patients"],
    queryFn: async () => unwrapListResponse(await apiClient.get<Patient[] | PaginatedResponse<Patient>>("/patients/")),
  });

  const form = useForm<ClinicalNoteValues>({
    resolver: zodResolver(clinicalNoteSchema),
    defaultValues: {
      patient: "",
      appointment: null,
      note_type: "progress",
      subjective: "",
      objective: "",
      assessment: "",
      plan: "",
      is_signed: true,
    },
  });

  const patientMap = useMemo(() => new Map((patientsQuery.data ?? []).map((patient) => [patient.id, patient.full_name])), [patientsQuery.data]);

  const noteMutation = useMutation({
    mutationFn: (values: ClinicalNoteValues) => apiClient.post("/clinical/notes/", values),
    onSuccess: () => {
      toast.success("Clinical note recorded.");
      queryClient.invalidateQueries({ queryKey: ["staff", "doctor", "appointments"] });
      form.reset({
        patient: "",
        appointment: null,
        note_type: "progress",
        subjective: "",
        objective: "",
        assessment: "",
        plan: "",
        is_signed: true,
      });
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Could not save note.");
    },
  });

  return (
    <RoleGate allow={["admin", "clinician"]}>
      <TopNav staff />
      <main className="page-shell py-10">
        <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <Card className="surface">
            <CardHeader>
              <CardTitle>Doctor schedule</CardTitle>
              <CardDescription>All appointments visible to clinical staff with quick note entry alongside the schedule.</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <THead>
                  <TR>
                    <TH>Status</TH>
                    <TH>Patient</TH>
                    <TH>Start</TH>
                    <TH>Reason</TH>
                  </TR>
                </THead>
                <TBody>
                  {appointmentsQuery.data?.map((appointment) => (
                    <TR
                      key={appointment.id}
                      className="cursor-pointer hover:bg-accent-soft/50"
                      onClick={() => {
                        form.setValue("appointment", appointment.id);
                        form.setValue("patient", appointment.patient);
                      }}
                    >
                      <TD>
                        <Badge>{appointment.status}</Badge>
                      </TD>
                      <TD>{patientMap.get(appointment.patient) ?? appointment.patient}</TD>
                      <TD>{formatDateTime(appointment.scheduled_start)}</TD>
                      <TD>{appointment.reason}</TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            </CardContent>
          </Card>
          <Card className="surface">
            <CardHeader>
              <CardTitle>Clinical note</CardTitle>
              <CardDescription>Select a row from the schedule, then write and sign the note.</CardDescription>
            </CardHeader>
            <CardContent>
              <form
                className="space-y-4"
                onSubmit={form.handleSubmit((values) => {
                  noteMutation.mutate(values);
                })}
              >
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="patient">Patient ID</Label>
                    <Input id="patient" {...form.register("patient")} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="note_type">Note type</Label>
                    <Input id="note_type" {...form.register("note_type")} />
                  </div>
                </div>
                <FormArea label="Subjective" id="subjective" register={form.register("subjective")} />
                <FormArea label="Objective" id="objective" register={form.register("objective")} />
                <FormArea label="Assessment" id="assessment" register={form.register("assessment")} />
                <FormArea label="Plan" id="plan" register={form.register("plan")} />
                <Button type="submit" variant="accent" disabled={noteMutation.isPending}>
                  {noteMutation.isPending ? "Saving..." : "Save signed note"}
                </Button>
              </form>
            </CardContent>
          </Card>
        </section>
      </main>
    </RoleGate>
  );
}

function FormArea({
  label,
  id,
  register,
}: {
  label: string;
  id: string;
  register: UseFormRegisterReturn;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Textarea id={id} {...register} />
    </div>
  );
}
