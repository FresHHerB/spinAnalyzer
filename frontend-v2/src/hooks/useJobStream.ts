import { useEffect, useState } from "react";
import { jobStreamUrl } from "@/lib/api";
import type { ProgressEvent } from "@/lib/api-types";

export function useJobStream(jobId: string | null) {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [status, setStatus] = useState<"idle" | "open" | "closed" | "error">(
    "idle",
  );

  useEffect(() => {
    if (!jobId) return;
    const ws = new WebSocket(jobStreamUrl(jobId));
    setStatus("open");
    setEvents([]);

    ws.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data) as ProgressEvent;
        setEvents((prev) => [...prev, data]);
        if (data.stage === "pipeline_done") {
          ws.close();
        }
      } catch {
        // ignore non-json
      }
    };
    ws.onerror = () => setStatus("error");
    ws.onclose = () => setStatus("closed");

    return () => {
      ws.close();
    };
  }, [jobId]);

  return { events, status };
}
