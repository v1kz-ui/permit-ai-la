"use client";
import { useState, useRef, useCallback } from "react";

interface UploadFile {
  file: File;
  preview?: string;
  progress: number;
  status: "pending" | "uploading" | "done" | "error";
}

interface Props {
  projectId: string;
  onUploadComplete?: (files: { name: string; size: number }[]) => void;
}

const ACCEPTED_TYPES = [
  "application/pdf",
  "image/jpeg",
  "image/png",
  "image/webp",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];

const MAX_SIZE = 25 * 1024 * 1024; // 25MB

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function getFileIcon(type: string): string {
  if (type.startsWith("image/")) return "\u{1F5BC}\uFE0F";
  if (type === "application/pdf") return "\u{1F4C4}";
  return "\u{1F4CE}";
}

export default function DocumentUpload({ projectId, onUploadComplete }: Props) {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const added: UploadFile[] = [];
    Array.from(newFiles).forEach((file) => {
      if (file.size > MAX_SIZE) return;
      const entry: UploadFile = { file, progress: 0, status: "pending" };
      if (file.type.startsWith("image/")) {
        entry.preview = URL.createObjectURL(file);
      }
      added.push(entry);
    });
    setFiles((prev) => [...prev, ...added]);
  }, []);

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => {
      const f = prev[index];
      if (f?.preview) URL.revokeObjectURL(f.preview);
      return prev.filter((_, i) => i !== index);
    });
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
  }, [addFiles]);

  const handleUpload = async () => {
    // Simulate upload (real implementation would call API)
    for (let i = 0; i < files.length; i++) {
      if (files[i].status !== "pending") continue;
      setFiles((prev) => prev.map((f, j) => j === i ? { ...f, status: "uploading" as const } : f));
      // Simulate progress
      for (let p = 0; p <= 100; p += 20) {
        await new Promise((r) => setTimeout(r, 200));
        setFiles((prev) => prev.map((f, j) => j === i ? { ...f, progress: p } : f));
      }
      setFiles((prev) => prev.map((f, j) => j === i ? { ...f, status: "done" as const, progress: 100 } : f));
    }
    onUploadComplete?.(files.map((f) => ({ name: f.file.name, size: f.file.size })));
  };

  const pendingCount = files.filter((f) => f.status === "pending").length;

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5">
      <h3 className="font-semibold text-slate-800 text-sm mb-3">Upload Documents</h3>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
          ${dragActive ? "border-indigo-400 bg-indigo-50" : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"}`}
        role="button"
        aria-label="Drop files or click to upload"
      >
        <svg className="w-8 h-8 mx-auto text-slate-400 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
        </svg>
        <p className="text-sm text-slate-600 font-medium">Drop files here or click to browse</p>
        <p className="text-xs text-slate-400 mt-1">PDF, images, DOCX up to 25 MB</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED_TYPES.join(",")}
          onChange={(e) => e.target.files && addFiles(e.target.files)}
          className="hidden"
          aria-hidden="true"
        />
      </div>

      {/* File previews */}
      {files.length > 0 && (
        <div className="mt-4 space-y-2">
          {files.map((f, i) => (
            <div key={`${f.file.name}-${i}`} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg border border-slate-100">
              {/* Thumbnail or icon */}
              {f.preview ? (
                <img src={f.preview} alt={f.file.name} className="w-10 h-10 rounded object-cover flex-shrink-0" />
              ) : (
                <span className="text-2xl flex-shrink-0 w-10 h-10 flex items-center justify-center">{getFileIcon(f.file.type)}</span>
              )}

              {/* File info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-700 truncate">{f.file.name}</p>
                <p className="text-xs text-slate-400">{formatFileSize(f.file.size)}</p>
                {f.status === "uploading" && (
                  <div className="mt-1 h-1 bg-slate-200 rounded-full overflow-hidden">
                    <div className="h-full bg-indigo-500 rounded-full transition-all" style={{ width: `${f.progress}%` }} />
                  </div>
                )}
              </div>

              {/* Status / remove */}
              {f.status === "done" ? (
                <svg className="w-5 h-5 text-emerald-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              ) : f.status === "pending" ? (
                <button onClick={() => removeFile(i)} className="text-slate-400 hover:text-red-500 transition-colors p-1" aria-label={`Remove ${f.file.name}`}>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              ) : null}
            </div>
          ))}
        </div>
      )}

      {/* Upload button */}
      {pendingCount > 0 && (
        <button
          onClick={handleUpload}
          className="mt-4 w-full bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium py-2.5 rounded-lg transition-colors"
        >
          Upload {pendingCount} file{pendingCount !== 1 ? "s" : ""}
        </button>
      )}
    </div>
  );
}
