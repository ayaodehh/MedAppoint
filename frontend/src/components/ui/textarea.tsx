import * as React from "react";

import { cn } from "@/lib/utils";

const Textarea = React.forwardRef<HTMLTextAreaElement, React.ComponentProps<"textarea">>(({ className, ...props }, ref) => {
  return (
    <textarea
      ref={ref}
      className={cn(
        "flex min-h-28 w-full rounded-2xl border border-line bg-paper px-4 py-3 text-sm text-ink outline-none transition placeholder:text-ink-muted/70 focus:border-accent",
        className,
      )}
      {...props}
    />
  );
});
Textarea.displayName = "Textarea";

export { Textarea };
