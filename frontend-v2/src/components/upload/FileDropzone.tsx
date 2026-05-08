import { useCallback, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { Upload as UploadIcon } from "lucide-react";

const ALLOWED = [".xml", ".txt", ".log", ".zip", ".phh"];

export function FileDropzone({
  onFiles,
  disabled,
}: {
  onFiles: (files: File[]) => void;
  disabled?: boolean;
}) {
  const [hover, setHover] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (list: FileList | null) => {
      if (!list) return;
      const files = Array.from(list).filter((f) =>
        ALLOWED.some((ext) => f.name.toLowerCase().endsWith(ext)),
      );
      if (files.length) onFiles(files);
    },
    [onFiles],
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setHover(true);
      }}
      onDragLeave={() => setHover(false)}
      onDrop={(e) => {
        e.preventDefault();
        setHover(false);
        if (!disabled) handleFiles(e.dataTransfer.files);
      }}
      onClick={() => !disabled && inputRef.current?.click()}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 text-center transition-colors",
        hover ? "border-primary bg-secondary/40" : "border-border",
        disabled && "cursor-not-allowed opacity-50",
      )}
    >
      <UploadIcon className="mb-3 h-10 w-10 text-muted-foreground" />
      <p className="text-sm font-medium">
        Drop hand-history files or click to browse
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        Accepts {ALLOWED.join(", ")}
      </p>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ALLOWED.join(",")}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  );
}
