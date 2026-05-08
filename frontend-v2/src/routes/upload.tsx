import { createFileRoute } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FileDropzone } from "@/components/upload/FileDropzone";
import { JobProgressStream } from "@/components/upload/JobProgressStream";

export const Route = createFileRoute("/upload")({
  component: UploadPage,
});

function UploadPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [mode, setMode] = useState<"arq" | "sync" | null>(null);

  const mutation = useMutation({
    mutationFn: () => api.upload(files),
    onSuccess: (res) => {
      setJobId(res.job_id);
      setMode(res.mode);
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold">Upload</h2>
        <p className="text-muted-foreground">
          Upload PHH / XML / TXT / ZIP hand-history files. The full ETL
          pipeline runs in the background.
        </p>
      </div>

      <FileDropzone onFiles={setFiles} disabled={mutation.isPending} />

      {files.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Selected files</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm">
              {files.map((f) => (
                <li key={f.name} className="font-mono">
                  {f.name}{" "}
                  <span className="text-muted-foreground">
                    ({(f.size / 1024).toFixed(1)} KB)
                  </span>
                </li>
              ))}
            </ul>
            <div className="mt-4 flex gap-2">
              <Button
                onClick={() => mutation.mutate()}
                disabled={mutation.isPending}
              >
                {mutation.isPending ? "Uploading…" : "Upload + process"}
              </Button>
              <Button
                variant="outline"
                onClick={() => setFiles([])}
                disabled={mutation.isPending}
              >
                Clear
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {jobId && (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <p className="text-sm">
              Job <code className="font-mono">{jobId}</code> queued.
            </p>
            {mode && (
              <Badge variant={mode === "arq" ? "default" : "secondary"}>
                {mode}
              </Badge>
            )}
          </div>
          {mode === "arq" ? (
            <JobProgressStream jobId={jobId} />
          ) : (
            <p className="text-sm text-muted-foreground">
              Sync mode (Redis unavailable) — pipeline runs in-process.
              Reload the dashboard once the request completes to see
              new villains.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
