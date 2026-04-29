"use client";

import { useRef, useState } from "react";
import { ArrowUp } from "lucide-react";

import { Nav } from "@/components/nav";
import { API_BASE } from "@/lib/api";
import { cn } from "@/lib/utils";

type Citation = {
  n: number;
  chemical: string;
  page: number | null;
  section: string | null;
  snippet: string;
};

export default function KnowledgePage() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function ask() {
    if (!question.trim() || loading) return;
    setAnswer("");
    setCitations([]);
    setLoading(true);

    try {
      const tenant = process.env.NEXT_PUBLIC_DEMO_TENANT_ID;
      const r = await fetch(`${API_BASE}/knowledge/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(tenant ? { "X-Tenant-Id": tenant } : {}),
        },
        body: JSON.stringify({ question }),
      });
      if (!r.ok || !r.body) {
        setAnswer("Sorry — the knowledge service is unavailable.");
        return;
      }
      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const event = JSON.parse(line);
            if (event.type === "citations") setCitations(event.citations);
            else if (event.type === "delta") setAnswer((prev) => prev + event.text);
          } catch {
            // ignore parse errors mid-chunk
          }
        }
      }
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      ask();
    }
  }

  return (
    <>
      <Nav />
      <main className="pt-nav">
        <div className="mx-auto max-w-prose px-3 py-7">
          <header className="mb-5 text-center">
            <h1 className="text-title-1 text-ink">Knowledge</h1>
            <p className="mt-1 text-body-lg text-ink-muted">
              Ask anything about your chemicals. Answers cite the EPA fact sheet inline.
            </p>
          </header>

          <div className="relative">
            <input
              ref={inputRef}
              autoFocus
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask anything about your chemicals."
              className={cn(
                "h-[56px] w-full rounded-pill border border-border bg-white pl-3 pr-7 text-body-lg text-ink placeholder:text-ink-muted",
                "transition-colors duration-quick ease-out",
                "focus:border-accent focus:shadow-focus focus:outline-none",
              )}
            />
            <button
              onClick={ask}
              disabled={!question.trim() || loading}
              className={cn(
                "absolute right-1 top-1/2 -translate-y-1/2 flex h-[40px] w-[40px] items-center justify-center rounded-full",
                "bg-accent text-white transition-opacity duration-quick disabled:opacity-30",
              )}
              aria-label="Ask"
            >
              <ArrowUp strokeWidth={1.5} className="h-2 w-2" />
            </button>
          </div>

          {(answer || loading) && (
            <article className="mt-6 text-body-lg text-ink whitespace-pre-wrap">
              {answer || <span className="text-ink-muted">Thinking…</span>}
            </article>
          )}

          {citations.length > 0 && (
            <section className="mt-6 border-t border-border-subtle pt-4">
              <p className="text-caption uppercase tracking-wide text-ink-muted">Citations</p>
              <ol className="mt-2 space-y-2">
                {citations.map((c) => (
                  <li key={c.n} className="text-body text-ink">
                    <span className="text-ink-muted num">⟨{c.n}⟩ </span>
                    <span className="font-medium">{c.chemical}</span>
                    {c.section && <span className="text-ink-muted"> · {c.section}</span>}
                    {c.page && <span className="text-ink-muted"> · p.{c.page}</span>}
                    <p className="mt-half text-caption text-ink-muted">{c.snippet}</p>
                  </li>
                ))}
              </ol>
            </section>
          )}
        </div>
      </main>
    </>
  );
}
