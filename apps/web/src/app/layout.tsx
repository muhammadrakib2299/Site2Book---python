import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Site2Book — Convert any website to a PDF eBook",
  description:
    "Paste a URL and get a clean, downloadable PDF with cover page, table of contents, and bookmarks.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen flex flex-col">
          <header className="border-b border-[var(--border)]">
            <div className="max-w-4xl mx-auto px-6 py-5 flex items-center justify-between">
              <a href="/" className="text-lg font-semibold tracking-tight">
                Site2Book
              </a>
              <a
                href="https://github.com/muhammadrakib2299/Site2Book---python"
                className="text-sm text-[var(--muted)] hover:text-white"
              >
                GitHub
              </a>
            </div>
          </header>
          <main className="flex-1">{children}</main>
          <footer className="border-t border-[var(--border)] text-[var(--muted)] text-sm">
            <div className="max-w-4xl mx-auto px-6 py-6">
              Built with FastAPI + Playwright + Next.js.
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
