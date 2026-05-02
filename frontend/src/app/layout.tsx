import type { Metadata } from "next";

import { AppProviders } from "@/components/providers/app-providers";

import "./globals.css";

export const metadata: Metadata = {
  title: "MedAppoint",
  description: "Patient and staff portal for clinic appointments, billing, clinical notes, and audit visibility.",
  icons: {
    icon: "/globe.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <body className="min-h-full bg-canvas text-ink antialiased" suppressHydrationWarning>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
