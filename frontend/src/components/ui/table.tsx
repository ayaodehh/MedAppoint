import type { HTMLAttributes, TableHTMLAttributes, TdHTMLAttributes, ThHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Table({ className, ...props }: TableHTMLAttributes<HTMLTableElement>) {
  return <table className={cn("w-full border-separate border-spacing-0", className)} {...props} />;
}

export function THead({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className={cn("[&_th]:border-b [&_th]:border-line [&_th]:pb-3 [&_th]:text-left", className)} {...props} />;
}

export function TBody({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={cn("[&_tr:last-child_td]:border-b-0", className)} {...props} />;
}

export function TR({ className, ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={cn("[&_td]:border-b [&_td]:border-line", className)} {...props} />;
}

export function TH({ className, ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return <th className={cn("px-4 text-xs font-semibold uppercase tracking-[0.2em] text-ink-muted", className)} {...props} />;
}

export function TD({ className, ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn("px-4 py-4 align-top text-sm text-panel", className)} {...props} />;
}
