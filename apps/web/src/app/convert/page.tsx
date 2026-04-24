"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { streamConvert, type ConvertEvent } from "@/lib/sse";

type Status =
  | { kind: "starting" }
  | { kind: "crawling"; url: string }
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

function ConvertInner() {
  const params = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<Status>({ kind: "starting" });
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

    const controller = new AbortController();
    streamConvert(
      { url, max_pages: maxPages, include_subdomains: includeSubdomains },
      (e: ConvertEvent) => {
        if (e.event === "crawling") setStatus({ kind: "crawling", url: e.url });
        else if (e.event === "rendering")
          setStatus({ kind: "rendering", page: e.page, total: e.total, url: e.url });
        else if (e.event === "merging") setStatus({ kind: "merging" });
        else if (e.event === "done")
          setStatus({
            kind: "done",
            downloadUrl: e.download_url,
            pages: e.pages,
            size: e.size_bytes,
            title: e.title,
          });
        else if (e.event === "error") setStatus({ kind: "error", message: e.message });
      },
      controller.signal,
    ).catch((err: Error) => {
      if (err.name !== "AbortError") setStatus({ kind: "error", message: err.message });
    });

    return () => controller.abort();
  }, [params, router]);

  return (
    <div className="max-w-2xl mx-auto px-6 py-16">
      <h1 className="text-3xl font-bold mb-2">
        {status.kind === "done"
          ? "Your eBook is ready"
          : status.kind === "error"
            ? "Something went wrong"
            : "Generating your eBook"}
      </h1>
      <p className="text-[var(--muted)] mb-10">
        {params.get("url")}
      </p>

      <div className="panel p-6">
        <ProgressRenderer status={status} />
      </div>

      {status.kind !== "done" && status.kind !== "error" && (
        <p className="mt-6 text-sm text-[var(--muted)]">
          Keep this tab open. Larger sites can take a minute or two.
        </p>
      )}

      <div className="mt-8">
        <button
          onClick={() => router.push("/")}
          className="text-sm text-[var(--muted)] hover:text-white"
        >
          ← Start over
        </button>
      </div>
    </div>
  );
}

function ProgressRenderer({ status }: { status: Status }) {
  if (status.kind === "starting") {
    return <Row label="Starting" sub="Waking up the browser..." pct={2} />;
  }
  if (status.kind === "crawling") {
    return <Row label="Crawling" sub={status.url} pct={15} />;
  }
  if (status.kind === "rendering") {
    const pct = 20 + Math.round((status.page / Math.max(status.total, 1)) * 65);
    return (
      <Row
        label={`Rendering ${status.page} of ${status.total}`}
        sub={status.url}
        pct={pct}
      />
    );
  }
  if (status.kind === "merging") {
    return <Row label="Merging" sub="Assembling cover, TOC, and chapters..." pct={92} />;
  }
  if (status.kind === "done") {
    return (
      <div className="space-y-5">
        <Row label="Done" sub={status.title} pct={100} />
        <div className="text-sm text-[var(--muted)]">
          {status.pages} pages · {(status.size / 1024).toFixed(0)} KB
        </div>
        <a href={status.downloadUrl} className="btn-primary inline-block">
          Download PDF
        </a>
      </div>
    );
  }
  return (
    <div className="text-red-400">
      <div className="font-semibold mb-1">Error</div>
      <div className="text-sm">{status.message}</div>
    </div>
  );
}

function Row({ label, sub, pct }: { label: string; sub?: string; pct: number }) {
  return (
    <div>
      <div className="flex items-baseline justify-between mb-2">
        <div className="font-semibold">{label}</div>
        <div className="text-sm text-[var(--muted)]">{pct}%</div>
      </div>
      {sub && <div className="text-sm text-[var(--muted)] mb-3 truncate">{sub}</div>}
      <div className="h-2 rounded-full bg-[#1c2128] overflow-hidden">
        <div
          className="h-full bg-[var(--accent)] transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function ConvertPage() {
  return (
    <Suspense fallback={<div className="max-w-2xl mx-auto px-6 py-16">Loading...</div>}>
      <ConvertInner />
    </Suspense>
  );
}
