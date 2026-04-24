import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";
import ThemeToggle from "@/components/ThemeToggle";

export const metadata: Metadata = {
  title: "Site2Book — Convert any website to a PDF eBook",
  description:
    "Paste a URL and get a clean, downloadable PDF with cover page, table of contents, and bookmarks.",
};

// Runs before React hydrates so the initial paint has the correct theme.
const themeBootScript = `
(function () {
  try {
    var saved = localStorage.getItem('site2book-theme');
    var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    var theme = saved || (prefersDark ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
  } catch (_) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
})();
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <Script id="theme-boot" strategy="beforeInteractive">
          {themeBootScript}
        </Script>
      </head>
      <body>
        <div className="min-h-screen flex flex-col">
          <header className="border-b border-[var(--border)] backdrop-blur bg-[var(--bg)]/70 sticky top-0 z-20">
            <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
              <a href="/" className="flex items-center gap-2 text-lg font-semibold tracking-tight">
                <span className="w-7 h-7 rounded-lg bg-[var(--accent)] text-white flex items-center justify-center text-sm">
                  S2B
                </span>
                Site2Book
              </a>
              <div className="flex items-center gap-1">
                <a
                  href="https://github.com/muhammadrakib2299/Site2Book---python"
                  target="_blank"
                  rel="noreferrer noopener"
                  className="btn-ghost text-sm hidden sm:inline-block"
                >
                  GitHub
                </a>
                <a
                  href="https://www.devrakib.com/"
                  target="_blank"
                  rel="noreferrer noopener"
                  className="btn-ghost text-sm hidden sm:inline-block"
                >
                  Portfolio
                </a>
                <ThemeToggle />
              </div>
            </div>
          </header>
          <main className="flex-1">{children}</main>
          <footer className="border-t border-[var(--border)] mt-20">
            <div className="max-w-5xl mx-auto px-6 py-10 grid sm:grid-cols-3 gap-8 text-sm">
              <div>
                <div className="font-semibold mb-2">Site2Book</div>
                <p className="text-[var(--muted)]">
                  Convert any website into a clean PDF eBook with cover, table of contents, and bookmarks.
                </p>
              </div>
              <div>
                <div className="font-semibold mb-2">Built with</div>
                <ul className="text-[var(--muted)] space-y-1">
                  <li>FastAPI + Playwright</li>
                  <li>pypdf · SQLModel</li>
                  <li>Next.js 15 · Tailwind</li>
                </ul>
              </div>
              <div>
                <div className="font-semibold mb-2">Links</div>
                <ul className="space-y-1">
                  <li>
                    <a
                      href="https://github.com/muhammadrakib2299/Site2Book---python"
                      target="_blank"
                      rel="noreferrer noopener"
                      className="text-[var(--muted)] hover:text-[var(--accent)]"
                    >
                      GitHub repository
                    </a>
                  </li>
                  <li>
                    <a
                      href="https://www.devrakib.com/"
                      target="_blank"
                      rel="noreferrer noopener"
                      className="text-[var(--muted)] hover:text-[var(--accent)]"
                    >
                      devrakib.com — portfolio
                    </a>
                  </li>
                </ul>
              </div>
            </div>
            <div className="border-t border-[var(--border)]">
              <div className="max-w-5xl mx-auto px-6 py-4 text-xs text-[var(--muted)] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <span>© {new Date().getFullYear()} Site2Book.</span>
                <span>
                  Crafted by{" "}
                  <a
                    href="https://www.devrakib.com/"
                    target="_blank"
                    rel="noreferrer noopener"
                    className="text-[var(--accent)] hover:underline"
                  >
                    devrakib.com
                  </a>
                </span>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
