import { cn } from "@/lib/utils";

export default function Card({ children, className }) {
  return (
    <div
      className={cn("bg-surface-raised border border-border p-8", className)}
    >
      {children}
    </div>
  );
}
