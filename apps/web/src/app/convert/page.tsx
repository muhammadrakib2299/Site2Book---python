"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { streamConvert, type ConvertEvent } from "@/lib/sse";

type Status =
  | { kind: "starting" }
  | { kind: "crawling"; url: string; found: number }
  | { kind: "browser_ready" }
  | { kind: "rendering"; page: number; total: number; url: string }
  | { kind: "merging" }
  | {
      kind: "done";
      downloadUrl: string;
      pages: number;
      size: number;
      title: string;
    }
  | { kind: "error"; message: string };

function absoluteDownload(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  const base = process.env.NEXT_PUBLIC_API_BASE || "";
  return base ? `${base}${path}` : path;
}

function ConvertInner() {
  const params = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<Status>({ kind: "starting" });
  const [elapsed, setElapsed] = useState(0);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    const url = params.get("url");
    const maxPages = Number(params.get("max_pages") ?? 20);
    const includeSubdomains = params.get("include_subdomains") === "1";
    if (!url) {
      router.replace("/");
      return;
    }

    const startTime = Date.now();
    const tick = setInterval(() => setElapsed(Math.floor((Date.now() - startTime) / 1000)), 500);

    const controller = new AbortController();
    streamConvert(
      { url, max_pages: maxPages, include_subdomains: includeSubdomains },
      (e: ConvertEvent) => {
        if (e.event === "crawling")
          setStatus({ kind: "crawling", url: e.url, found: e.found ?? 0 });
        else if (e.event === "browser_ready") setStatus({ kind: "browser_ready" });
        else if (e.event === "rendering")
          setStatus({ kind: "rendering", page: e.page, total: e.total, url: e.url });
        else if (e.event === "merging") setStatus({ kind: "merging" });
        else if (e.event === "done") {
          setStatus({
            kind: "done",
            downloadUrl: absoluteDownload(e.download_url),
            pages: e.pages,
            size: e.size_bytes,
            title: e.title,
          });
          clearInterval(tick);
        } else if (e.event === "error") {
          setStatus({ kind: "error", message: e.message });
          clearInterval(tick);
        }
      },
      controller.signal,
    ).catch((err: Error) => {
      if (err.name !== "AbortError") setStatus({ kind: "error", message: err.message });
      clearInterval(tick);
    });

    return () => {
      controller.abort();
      clearInterval(tick);
    };
  }, [params, router]);

  const sourceUrl = params.get("url") ?? "";

  return (
    <div className="max-w-2xl mx-auto px-6 py-16">
      <div className="mb-8">
        <div className="text-xs text-[var(--muted)] uppercase tracking-widest mb-2">
          {status.kind === "done"
            ? "Complete"
            : status.kind === "error"
              ? "Error"
              : "In progress"}
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold mb-2">
          {status.kind === "done"
            ? "Your eBook is ready"
            : status.kind === "error"
              ? "Something went wrong"
              : "Generating your eBook"}
        </h1>
        <p className="text-[var(--muted)] break-all text-sm">{sourceUrl}</p>
      </div>

      <div className="panel p-6 sm:p-8">
        <ProgressRenderer status={status} elapsed={elapsed} />
      </div>

      {status.kind !== "done" && status.kind !== "error" && (
        <p className="mt-6 text-sm text-[var(--muted)]">
          <TimerIcon /> Elapsed {elapsed}s · Keep this tab open. Larger sites can take a minute or two.
        </p>
      )}

      <div className="mt-8">
        <button onClick={() => router.push("/")} className="btn-ghost text-sm">
          ← Start over
        </button>
      </div>
    </div>
  );
}

function ProgressRenderer({ status, elapsed }: { status: Status; elapsed: number }) {
  if (status.kind === "starting") {
    return <StepRow label="Connecting to the server" sub={`Opening stream... ${elapsed}s`} pct={4} />;
  }
  if (status.kind === "crawling") {
    const pct = Math.min(18, 4 + (status.found ?? 0) * 1.5);
    return (
      <StepRow
        label="Crawling pages"
        sub={
          status.found > 0
            ? `${status.found} page${status.found === 1 ? "" : "s"} found · latest: ${status.url}`
            : `Discovering pages... ${status.url}`
        }
        pct={pct}
      />
    );
  }
  if (status.kind === "browser_ready") {
    return <StepRow label="Browser ready" sub="Preparing to render..." pct={22} />;
  }
  if (status.kind === "rendering") {
    const pct = 25 + Math.round((status.page / Math.max(status.total, 1)) * 65);
    return (
      <StepRow
        label={`Rendering page ${status.page} of ${status.total}`}
        sub={status.url}
        pct={pct}
      />
    );
  }
  if (status.kind === "merging") {
    return <StepRow label="Merging" sub="Assembling cover, TOC, and bookmarks..." pct={94} />;
  }
  if (status.kind === "done") {
    return (
      <div className="space-y-6">
        <StepRow label="Done" sub={status.title} pct={100} done />
        <div className="flex flex-wrap items-center gap-4 text-sm text-[var(--muted)]">
          <Stat label="Pages" value={String(status.pages)} />
          <Stat label="Size" value={`${(status.size / 1024).toFixed(0)} KB`} />
          <Stat label="Time" value={`${elapsed}s`} />
        </div>
        <a href={status.downloadUrl} className="btn-primary inline-flex items-center gap-2" download>
          <DownloadIcon /> Download PDF
        </a>
      </div>
    );
  }
  return (
    <div>
      <div className="flex items-center gap-2 text-[var(--danger)] font-semibold mb-2">
        <ErrorIcon /> Error
      </div>
      <div className="text-sm text-[var(--text-dim)]">{status.message}</div>
    </div>
  );
}

function StepRow({
  label,
  sub,
  pct,
  done = false,
}: {
  label: string;
  sub?: string;
  pct: number;
  done?: boolean;
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between mb-2">
        <div className="flex items-center gap-2 font-semibold">
          {!done && <span className="w-2 h-2 rounded-full bg-[var(--accent)] pulse-dot" />}
          {done && <span className="text-[var(--success)]"><CheckIcon /></span>}
          {label}
        </div>
        <div className="text-xs text-[var(--muted)] font-variant-tabular">{Math.round(pct)}%</div>
      </div>
      {sub && (
        <div className="text-sm text-[var(--muted)] mb-3 truncate" title={sub}>
          {sub}
        </div>
      )}
      <div className="h-2 rounded-full bg-[var(--panel-2)] overflow-hidden border border-[var(--border)]">
        <div
          className={`h-full transition-all duration-500 ${done ? "bg-[var(--success)]" : "shimmer-bar"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="panel-soft px-3 py-2">
      <div className="text-xs text-[var(--muted)]">{label}</div>
      <div className="font-semibold text-[var(--text)]">{value}</div>
    </div>
  );
}

function CheckIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
  );
}
function DownloadIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>
  );
}
function TimerIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="inline-block mr-1 -mt-0.5"><circle cx="12" cy="13" r="8" /><path d="M12 9v4l2 2M9 3h6" /></svg>
  );
}
function ErrorIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>
  );
}

export default function ConvertPage() {
  return (
    <Suspense fallback={<div className="max-w-2xl mx-auto px-6 py-16">Loading...</div>}>
      <ConvertInner />
    </Suspense>
  );
}
