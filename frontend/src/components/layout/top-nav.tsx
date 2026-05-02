"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { CalendarDays, ClipboardList, LogOut, Shield, Stethoscope } from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "@/hooks/use-auth";

import { Button } from "@/components/ui/button";

const patientLinks = [
  { href: "/dashboard", label: "Dashboard", icon: ClipboardList },
  { href: "/book", label: "Book", icon: CalendarDays },
  { href: "/appointments", label: "My Visits", icon: CalendarDays },
];

const staffLinks = [
  { href: "/staff/appointments", label: "Reception", icon: ClipboardList },
  { href: "/staff/schedule", label: "Doctor", icon: Stethoscope },
  { href: "/staff/audit", label: "Audit", icon: Shield },
];

export function TopNav({ staff = false }: { staff?: boolean }) {
  const router = useRouter();
  const { user, logout } = useAuth();
  const links = staff ? staffLinks : patientLinks;

  return (
    <header className="sticky top-0 z-20 border-b border-line bg-paper/90 backdrop-blur">
      <div className="page-shell flex items-center justify-between gap-6 py-4">
        <div>
          <p className="font-serif text-2xl font-semibold tracking-tight text-panel">MedAppoint</p>
          <p className="text-sm text-ink-muted">{staff ? "Staff operations" : "Patient self-service"}</p>
        </div>
        <nav className="hidden items-center gap-2 md:flex">
          {links.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className="inline-flex items-center gap-2 rounded-full border border-transparent px-4 py-2 text-sm font-medium text-ink-muted transition hover:border-line hover:bg-accent-soft hover:text-panel"
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          <div className="text-right text-sm">
            <p className="font-medium text-panel">{user ? `${user.first_name || user.username}` : "Guest"}</p>
            <p className="text-ink-muted">{user?.role ?? "public"}</p>
          </div>
          {user ? (
            <Button
              variant="ghost"
              onClick={() => {
                logout.mutate(undefined, {
                  onSuccess: () => {
                    toast.success("Signed out.");
                    router.push(staff ? "/staff/login" : "/login");
                  },
                });
              }}
            >
              <LogOut className="mr-2 h-4 w-4" />
              Logout
            </Button>
          ) : null}
        </div>
      </div>
    </header>
  );
}
