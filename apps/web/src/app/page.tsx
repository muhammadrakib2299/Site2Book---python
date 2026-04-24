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
    <div className="max-w-3xl mx-auto px-6 py-16 sm:py-24">
      <div className="mb-8 flex justify-center">
        <span className="hero-pill">
          <span className="hero-pill-dot" />
          Free · No sign-up required
        </span>
      </div>

      <h1 className="text-4xl sm:text-6xl font-bold tracking-tight text-center mb-4 leading-[1.05]">
        Convert any website <br className="hidden sm:inline" />
        into a <span className="grad-text">PDF eBook</span>
      </h1>
      <p className="text-[var(--text-dim)] text-center mb-12 text-lg max-w-xl mx-auto">
        Paste a URL. We crawl internal pages, render each one cleanly, and merge
        them into a single polished PDF with cover, table of contents, and
        clickable bookmarks.
      </p>

      <form onSubmit={onSubmit} className="panel p-6 sm:p-8 space-y-6">
        <label className="block">
          <span className="text-sm font-medium mb-2 block">Website URL</span>
          <div className="relative">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none">
              <LinkIcon />
            </span>
            <input
              type="url"
              placeholder="https://example.com/docs/"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
              autoFocus
              style={{ paddingLeft: 42 }}
            />
          </div>
        </label>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <label className="block">
            <span className="text-sm font-medium mb-2 block">Max pages</span>
            <select
              value={maxPages}
              onChange={(e) => setMaxPages(Number(e.target.value))}
            >
              <option value={5}>5 pages (fast)</option>
              <option value={10}>10 pages</option>
              <option value={20}>20 pages</option>
              <option value={50}>50 pages</option>
            </select>
          </label>
          <label className="flex items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-4 py-3 mt-0 sm:mt-7 cursor-pointer">
            <input
              type="checkbox"
              checked={includeSubdomains}
              onChange={(e) => setIncludeSubdomains(e.target.checked)}
              className="w-4 h-4"
            />
            <span className="text-sm">Include subdomains</span>
          </label>
        </div>

        <label className="flex items-start gap-3 text-sm text-[var(--text-dim)]">
          <input
            type="checkbox"
            checked={agreed}
            onChange={(e) => setAgreed(e.target.checked)}
            className="w-4 h-4 mt-0.5"
          />
          <span>
            I confirm I have the right to convert this content and will respect
            the source site&apos;s terms of service and copyright.
          </span>
        </label>

        {error && (
          <div className="text-sm text-[var(--danger)] bg-red-500/10 border border-red-500/25 px-3 py-2 rounded-lg">
            {error}
          </div>
        )}

        <button type="submit" className="btn-primary w-full sm:w-auto">
          Generate eBook →
        </button>
      </form>

      <div className="mt-16 grid sm:grid-cols-3 gap-4">
        <Feature
          icon={<TocIcon />}
          title="Cover & Table of Contents"
          body="Every eBook gets a cover page with source info and a clickable TOC with accurate page numbers."
        />
        <Feature
          icon={<ShieldIcon />}
          title="Respects robots.txt"
          body="Same-origin by default, path-prefix scoped, and we honor crawl rules. No abusive scraping."
        />
        <Feature
          icon={<BoltIcon />}
          title="Real browser rendering"
          body="Playwright Chromium with print-media CSS. Ads, cookie banners, and chat widgets are stripped."
        />
      </div>
    </div>
  );
}

function Feature({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  return (
    <div className="feature-card">
      <div className="w-9 h-9 rounded-lg bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center mb-3">
        {icon}
      </div>
      <div className="font-semibold mb-1">{title}</div>
      <p className="text-sm text-[var(--muted)] leading-relaxed">{body}</p>
    </div>
  );
}

function LinkIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </svg>
  );
}
function TocIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 6h18M3 12h18M3 18h12" />
    </svg>
  );
}
function ShieldIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}
function BoltIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  );
}
