export type Role = "admin" | "clinician" | "receptionist" | "billing" | "patient" | "auditor";

export type User = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  phone_number: string;
  role: Role;
  otp_required: boolean;
  is_active: boolean;
};

export type Patient = {
  id: string;
  user: number | null;
  full_name: string;
  medical_record_number: string;
  date_of_birth: string;
  sex: string;
  phone_number: string;
  emergency_contact: string;
  address: string;
  allergies: string;
  insurance_provider: string;
  insurance_number: string;
  active: boolean;
  created_at: string;
  updated_at: string;
};

export type Appointment = {
  id: number;
  patient: string;
  clinician: number | null;
  scheduled_start: string;
  scheduled_end: string;
  status: "requested" | "confirmed" | "completed" | "cancelled" | "no_show";
  reason: string;
  notes: string;
  created_by: number | null;
  last_updated_by: number | null;
  created_at: string;
  updated_at: string;
};

export type ClinicalNote = {
  id: number;
  patient: string;
  appointment: number | null;
  author: number | null;
  note_type: string;
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
  is_signed: boolean;
  signed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type Invoice = {
  id: number;
  patient: string;
  appointment: number | null;
  amount_due: string;
  currency: string;
  status: "draft" | "pending" | "paid" | "failed" | "void";
  issued_at: string;
  due_at: string | null;
  paid_at: string | null;
  created_by: number | null;
  external_reference: string;
  last_gateway_payload: Record<string, unknown>;
};

export type AuditLogEntry = {
  id: number;
  actor: number | null;
  action: string;
  resource_type: string;
  resource_id: string;
  status: "success" | "failure";
  ip_address: string | null;
  user_agent: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type ApiErrorResponse = {
  detail?: string;
  [key: string]: unknown;
};

export type PaginatedResponse<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};
