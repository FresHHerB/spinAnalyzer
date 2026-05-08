import { useJobStream } from "@/hooks/useJobStream";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function JobProgressStream({ jobId }: { jobId: string }) {
  const { events, status } = useJobStream(jobId);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Job {jobId}</CardTitle>
        <p className="text-xs text-muted-foreground">stream: {status}</p>
      </CardHeader>
      <CardContent>
        {events.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Waiting for progress events…
          </p>
        ) : (
          <ol className="space-y-1 font-mono text-xs">
            {events.map((e, i) => (
              <li key={i} className="text-muted-foreground">
                <span className="font-semibold text-foreground">
                  {e.stage}
                </span>
                {" "}
                {Object.entries(e)
                  .filter(([k]) => k !== "stage")
                  .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
                  .join(" ")}
              </li>
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}
