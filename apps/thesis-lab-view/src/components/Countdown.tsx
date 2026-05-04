import { useEffect, useState } from "react";
import { fmtCountdown } from "@/lib/format";

export function Countdown({ iso, className }: { iso: string; className?: string }) {
  const [, tick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => tick(t => t + 1), 1000);
    return () => clearInterval(id);
  }, []);
  return <span className={className + " font-mono tabular"}>{fmtCountdown(iso)}</span>;
}
