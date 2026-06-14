"use client";

import { useState, useRef, useCallback } from "react";

interface SSEOptions {
  onToken?: (fullText: string, token: string) => void;
  onDone?: (fullText: string) => void;
  onError?: (error: Error) => void;
  onTrace?: (event: Record<string, unknown>) => void;
  headers?: Record<string, string>;
}

interface SSEState {
  isStreaming: boolean;
  text: string;
  error: string | null;
  trace: unknown;
}

export function useSSE() {
  const [state, setState] = useState<SSEState>({
    isStreaming: false,
    text: "",
    error: null,
    trace: null,
  });
  const abortRef = useRef<AbortController | null>(null);

  const start = useCallback(async (url: string, body: unknown, options: SSEOptions = {}) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState({ isStreaming: true, text: "", error: null, trace: null });

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080/api/v1";
      const fetchHeaders: Record<string, string> = {
        "Content-Type": "application/json",
        ...options.headers,
      };
      const response = await fetch(`${apiBase}${url}`, {
        method: "POST",
        headers: fetchHeaders,
        credentials: "include",
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Stream error" }));
        throw new Error(err.detail || `HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";
      let fullText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;

          const data = line.slice(6).trim();
          if (data === "[DONE]") continue;

          try {
            const parsed = JSON.parse(data);

            const token = parsed.text || parsed.token;
            if (token) {
              fullText += token;
              setState((s) => ({ ...s, text: fullText }));
              options.onToken?.(fullText, token);
            }

            if (parsed.tool_name || parsed.run_id || parsed.tokens_used !== undefined || parsed.trace) {
              setState((s) => ({ ...s, trace: parsed }));
              options.onTrace?.(parsed as Record<string, unknown>);
            }
          } catch {
            fullText += data;
            setState((s) => ({ ...s, text: fullText }));
            options.onToken?.(fullText, data);
          }
        }
      }

      setState((s) => ({ ...s, isStreaming: false }));
      options.onDone?.(fullText);
    } catch (err: any) {
      if (err.name === "AbortError") {
        setState((s) => ({ ...s, isStreaming: false }));
        return;
      }
      const message = err.message || "Stream error";
      setState({ isStreaming: false, text: "", error: message, trace: null });
      options.onError?.(err);
    }
  }, []);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setState((s) => ({ ...s, isStreaming: false }));
  }, []);

  return { ...state, start, stop };
}
