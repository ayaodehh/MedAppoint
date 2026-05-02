"use client";

import { useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { RoleGate } from "@/components/auth/role-gate";
import { TopNav } from "@/components/layout/top-nav";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { apiClient, unwrapListResponse } from "@/lib/api-client";
import { bookAppointmentSchema } from "@/lib/schemas";
import type { PaginatedResponse, Patient } from "@/lib/types";

type BookAppointmentValues = z.infer<typeof bookAppointmentSchema>;

export default function BookPage() {
  const router = useRouter();
  const patientQuery = useQuery({
    queryKey: ["patients", "mine"],
    queryFn: async () => {
      const patients = await apiClient.get<Patient[] | PaginatedResponse<Patient>>("/patients/");
      return unwrapListResponse(patients)[0] ?? null;
    },
  });

  const patientId = useMemo(() => patientQuery.data?.id ?? "", [patientQuery.data]);

  const form = useForm<BookAppointmentValues>({
    resolver: zodResolver(bookAppointmentSchema),
    defaultValues: {
      patient: patientId,
      scheduled_start: "",
      scheduled_end: "",
      reason: "",
      notes: "",
    },
  });

  useEffect(() => {
    if (!patientId) {
      return;
    }

    form.setValue("patient", patientId, { shouldValidate: true });
  }, [form, patientId]);

  const mutation = useMutation({
    mutationFn: (values: BookAppointmentValues) => apiClient.post("/appointments/", values),
    onSuccess: () => {
      toast.success("Appointment request submitted.");
      router.push("/appointments");
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Could not create appointment.");
    },
  });

  return (
    <RoleGate allow={["patient"]}>
      <TopNav />
      <main className="page-shell py-10">
        <Card className="surface mx-auto max-w-3xl">
          <CardHeader>
            <CardTitle>Book an appointment</CardTitle>
            <CardDescription>Requests are sent to reception and stay tied to your patient profile.</CardDescription>
          </CardHeader>
          <CardContent>
            <form
              className="grid gap-5 md:grid-cols-2"
              onSubmit={form.handleSubmit((values) => {
                mutation.mutate(values);
              })}
            >
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="patient">Patient record</Label>
                <Input id="patient" value={patientQuery.data?.full_name ?? "Loading patient profile..."} readOnly />
              </div>
              <div className="space-y-2">
                <Label htmlFor="scheduled_start">Start</Label>
                <Input id="scheduled_start" type="datetime-local" {...form.register("scheduled_start")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="scheduled_end">End</Label>
                <Input id="scheduled_end" type="datetime-local" {...form.register("scheduled_end")} />
              </div>
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="reason">Reason</Label>
                <Input id="reason" {...form.register("reason")} />
              </div>
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="notes">Notes</Label>
                <Textarea id="notes" {...form.register("notes")} />
              </div>
              <div className="md:col-span-2">
                <Button type="submit" variant="accent" disabled={mutation.isPending || !patientId}>
                  {mutation.isPending ? "Submitting..." : "Submit request"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </main>
    </RoleGate>
  );
}
