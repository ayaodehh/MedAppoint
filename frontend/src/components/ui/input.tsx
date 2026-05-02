import * as React from "react";

import { cn } from "@/lib/utils";

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(({ className, ...props }, ref) => {
  return (
    <input
      ref={ref}
      className={cn(
        "flex h-11 w-full rounded-2xl border border-line bg-paper px-4 py-2 text-sm text-ink outline-none transition placeholder:text-ink-muted/70 focus:border-accent",
        className,
      )}
      {...props}
    />
  );
});
Input.displayName = "Input";

export { Input };
