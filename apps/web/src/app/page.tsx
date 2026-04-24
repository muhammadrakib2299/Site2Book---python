"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function HomePage() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [maxPages, setMaxPages] = useState(20);
  const [includeSubdomains, setIncludeSubdomains] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      new URL(url);
    } catch {
      setError("Please enter a valid URL (including https://).");
      return;
    }
    if (!agreed) {
      setError("Please confirm you have rights to convert this content.");
      return;
    }
    const params = new URLSearchParams({
      url,
      max_pages: String(maxPages),
      include_subdomains: includeSubdomains ? "1" : "0",
    });
    router.push(`/convert?${params.toString()}`);
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-16">
      <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-3">
        Convert any website to a PDF eBook
      </h1>
      <p className="text-[var(--muted)] mb-10 text-lg">
        Paste a URL. We crawl internal pages, render each one cleanly, and
        merge them into one PDF with cover, table of contents, and bookmarks.
      </p>

      <form onSubmit={onSubmit} className="panel p-6 space-y-5">
        <label className="block">
          <span className="text-sm text-[var(--muted)] mb-2 block">Website URL</span>
          <input
            type="url"
            placeholder="https://example.com/docs/"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
            autoFocus
          />
        </label>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <label className="block">
            <span className="text-sm text-[var(--muted)] mb-2 block">Max pages</span>
            <select
              value={maxPages}
              onChange={(e) => setMaxPages(Number(e.target.value))}
            >
              <option value={10}>10 pages</option>
              <option value={20}>20 pages</option>
              <option value={50}>50 pages</option>
            </select>
          </label>
          <label className="flex items-center gap-3 mt-7">
            <input
              type="checkbox"
              checked={includeSubdomains}
              onChange={(e) => setIncludeSubdomains(e.target.checked)}
              className="w-4 h-4"
            />
            <span className="text-sm">Include subdomains</span>
          </label>
        </div>

        <label className="flex items-start gap-3 text-sm text-[var(--muted)]">
          <input
            type="checkbox"
            checked={agreed}
            onChange={(e) => setAgreed(e.target.checked)}
            className="w-4 h-4 mt-0.5"
          />
          <span>
            I confirm I have the right to convert this content. I will respect
            the source site's terms and copyright.
          </span>
        </label>

        {error && (
          <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 px-3 py-2 rounded-lg">
            {error}
          </div>
        )}

        <button type="submit" className="btn-primary w-full sm:w-auto">
          Generate eBook
        </button>
      </form>

      <div className="mt-10 text-sm text-[var(--muted)] space-y-2">
        <p>
          <strong className="text-white">Good for:</strong> documentation,
          blog archives, long-form articles, personal references.
        </p>
        <p>
          <strong className="text-white">Respects:</strong> robots.txt,
          same-origin by default, path-prefix scoping.
        </p>
      </div>
    </div>
  );
}
