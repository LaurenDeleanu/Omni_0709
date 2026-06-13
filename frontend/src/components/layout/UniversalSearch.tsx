"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Search, X, Loader2, User, Bot, Folder, GraduationCap, Briefcase } from "lucide-react";
import { useRouter } from "@/i18n/routing";
import { API_BASE } from "@/lib/api/client";

interface SearchResult {
  id: string;
  type: "employee" | "agent" | "project" | "course" | "job";
  title: string;
  subtitle: string;
  route: string;
}

const TYPE_ICONS: Record<string, React.ReactNode> = {
  employee: <User size={14} />,
  agent: <Bot size={14} />,
  project: <Folder size={14} />,
  course: <GraduationCap size={14} />,
  job: <Briefcase size={14} />,
};

export function UniversalSearch() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen(true);
      }
      if (e.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const search = useCallback(async (q: string) => {
    if (q.length < 1) {
      setResults([]);
      return;
    }
    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/search?q=${encodeURIComponent(q)}`, {
        credentials: "include",
        signal: controller.signal,
      });
      if (resp.ok) {
        const data = await resp.json();
        setResults(data.slice(0, 8));
        setSelectedIndex(0);
      }
    } catch (e: any) {
      if (e.name !== "AbortError") console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  const navigateTo = (result: SearchResult) => {
    setOpen(false);
    setQuery("");
    setResults([]);
    router.push(result.route);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex(i => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex(i => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && results[selectedIndex]) {
      e.preventDefault();
      navigateTo(results[selectedIndex]);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border/40 bg-muted/30 text-muted-foreground text-xs hover:bg-muted/60 transition-colors min-w-[200px]"
      >
        <Search size={14} />
        <span className="flex-1 text-left">Type / to search...</span>
        <kbd className="px-1.5 py-0.5 rounded bg-background border text-[10px]">⌘K</kbd>
      </button>
    );
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]" onClick={() => setOpen(false)}>
      <div className="absolute inset-0 bg-background/80 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-lg rounded-xl border bg-background shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 px-4 py-3 border-b">
          <Search size={16} className="text-muted-foreground" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => { setQuery(e.target.value); search(e.target.value); }}
            onKeyDown={handleKeyDown}
            placeholder="Search employees, agents, projects..."
            className="flex-1 bg-transparent border-none outline-none text-sm"
          />
          {loading && <Loader2 size={14} className="animate-spin text-muted-foreground" />}
          <button onClick={() => setOpen(false)} className="text-muted-foreground hover:text-foreground">
            <X size={16} />
          </button>
        </div>
        {results.length > 0 && (
          <div className="max-h-[300px] overflow-y-auto py-2">
            {results.map((r, i) => (
              <button
                key={r.id}
                onClick={() => navigateTo(r)}
                onMouseEnter={() => setSelectedIndex(i)}
                className={`w-full flex items-center gap-3 px-4 py-2 text-sm transition-colors ${i === selectedIndex ? "bg-accent" : "hover:bg-muted/50"}`}
              >
                <span className="text-muted-foreground">{TYPE_ICONS[r.type] || <Search size={14} />}</span>
                <div className="flex-1 text-left">
                  <div className="font-medium">{r.title}</div>
                  <div className="text-xs text-muted-foreground">{r.subtitle}</div>
                </div>
                <span className="text-[10px] text-muted-foreground uppercase">{r.type}</span>
              </button>
            ))}
          </div>
        )}
        {query.length >= 1 && !loading && results.length === 0 && (
          <div className="px-4 py-8 text-center text-sm text-muted-foreground">No results found</div>
        )}
      </div>
    </div>
  );
}
