import { z } from "zod";

export const registerSchema = z.object({
  username: z.string().min(3),
  email: z.email(),
  first_name: z.string().min(2),
  last_name: z.string().min(2),
  phone_number: z.string().min(7),
  password: z.string().min(8),
  medical_record_number: z.string().min(4),
  date_of_birth: z.string().min(1),
});

export const loginSchema = z.object({
  username: z.string().min(1),
  password: z.string().min(1),
  otp_token: z.string().optional(),
});

export const bookAppointmentSchema = z.object({
  patient: z.string().min(1),
  scheduled_start: z.string().min(1),
  scheduled_end: z.string().min(1),
  reason: z.string().min(4),
  notes: z.string().optional(),
});

export const completeAndBillSchema = z.object({
  amount_due: z.coerce.number().positive(),
  currency: z.string().min(3).max(3),
  due_at: z.string().min(1),
});

export const clinicalNoteSchema = z.object({
  patient: z.string().min(1),
  appointment: z.number().nullable().optional(),
  note_type: z.string().min(2),
  subjective: z.string().min(2),
  objective: z.string().min(2),
  assessment: z.string().min(2),
  plan: z.string().min(2),
  is_signed: z.boolean(),
});

export const stepUpSchema = z.object({
  password: z.string().min(1),
});
