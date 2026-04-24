export type ConvertEvent =
  | { event: "crawling"; url: string }
  | { event: "rendering"; page: number; total: number; url: string }
  | { event: "merging" }
  | {
      event: "done";
      token: string;
      download_url: string;
      pages: number;
      size_bytes: number;
      title: string;
    }
  | { event: "error"; message: string };

export interface ConvertInput {
  url: string;
  max_pages: number;
  include_subdomains: boolean;
  title?: string;
}

/**
 * Start a conversion and stream progress events.
 *
 * Native EventSource can't POST, so we use fetch + a ReadableStream and
 * parse the `data:` lines of the SSE framing ourselves.
 */
export async function streamConvert(
  input: ConvertInput,
  onEvent: (e: ConvertEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const resp = await fetch("/api/convert", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(input),
    signal,
  });

  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new Error(`HTTP ${resp.status}: ${text || resp.statusText}`);
  }

  const reader = resp.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let idx;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const dataLines = frame
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trim());
      if (!dataLines.length) continue;
      try {
        const parsed = JSON.parse(dataLines.join("\n")) as ConvertEvent;
        onEvent(parsed);
      } catch {
        /* ignore malformed frame */
      }
    }
  }
}
