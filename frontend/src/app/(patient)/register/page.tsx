"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, type UseFormRegisterReturn } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { useAuth } from "@/hooks/use-auth";
import { registerSchema } from "@/lib/schemas";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type RegisterFormValues = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();
  const form = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      username: "",
      email: "",
      first_name: "",
      last_name: "",
      phone_number: "",
      password: "",
      medical_record_number: "",
      date_of_birth: "",
    },
  });

  return (
    <main className="page-shell py-16">
      <Card className="surface mx-auto max-w-3xl">
        <CardHeader>
          <CardTitle>New patient registration</CardTitle>
          <CardDescription>Create your portal account and link it to a clinic medical record number.</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="grid gap-5 md:grid-cols-2"
            onSubmit={form.handleSubmit((values) => {
              register.mutate(values, {
                onSuccess: () => {
                  toast.success("Account created.");
                  router.push("/dashboard");
                },
                onError: (error) => {
                  toast.error(error instanceof Error ? error.message : "Registration failed.");
                },
              });
            })}
          >
            <Field label="Username" id="username" register={form.register("username")} />
            <Field label="Email" id="email" type="email" register={form.register("email")} />
            <Field label="First name" id="first_name" register={form.register("first_name")} />
            <Field label="Last name" id="last_name" register={form.register("last_name")} />
            <Field label="Phone number" id="phone_number" register={form.register("phone_number")} />
            <Field label="Medical record number" id="medical_record_number" register={form.register("medical_record_number")} />
            <Field label="Date of birth" id="date_of_birth" type="date" register={form.register("date_of_birth")} />
            <Field label="Password" id="password" type="password" register={form.register("password")} />
            <div className="md:col-span-2 flex flex-col gap-4">
              <Button type="submit" variant="accent" disabled={register.isPending}>
                {register.isPending ? "Creating account..." : "Create account"}
              </Button>
              <p className="text-sm text-ink-muted">
                Already registered?{" "}
                <Link className="font-semibold text-accent-strong" href="/login">
                  Sign in
                </Link>
              </p>
            </div>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}

function Field({
  label,
  id,
  register,
  type = "text",
}: {
  label: string;
  id: string;
  register: UseFormRegisterReturn;
  type?: string;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} type={type} {...register} />
    </div>
  );
}
