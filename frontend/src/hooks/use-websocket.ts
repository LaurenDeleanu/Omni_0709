"use client";

import { useEffect, useRef, useCallback, useState } from "react";

interface UseWebSocketOptions {
  url: string;
  onMessage?: (event: MessageEvent) => void;
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
  reconnect?: boolean;
  reconnectIntervalMs?: number;
  maxReconnectAttempts?: number;
  enabled?: boolean;
}

interface WebSocketState {
  readyState: number;
  reconnectAttempt: number;
  connected: boolean;
  error: string | null;
}

const DEFAULT_RECONNECT_INTERVAL = 1000;
const MAX_RECONNECT_INTERVAL = 30000;
const DEFAULT_MAX_ATTEMPTS = 10;

export function useWebSocket({
  url,
  onMessage,
  onOpen,
  onClose,
  onError,
  reconnect = true,
  reconnectIntervalMs = DEFAULT_RECONNECT_INTERVAL,
  maxReconnectAttempts = DEFAULT_MAX_ATTEMPTS,
  enabled = true,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const callbacksRef = useRef({ onMessage, onOpen, onClose, onError });
  const [state, setState] = useState<WebSocketState>({
    readyState: WebSocket.CLOSED,
    reconnectAttempt: 0,
    connected: false,
    error: null,
  });

  callbacksRef.current = { onMessage, onOpen, onClose, onError };

  const connect = useCallback(() => {
    if (!enabled || !url) return;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = (event) => {
        reconnectAttemptRef.current = 0;
        setState({
          readyState: WebSocket.OPEN,
          reconnectAttempt: 0,
          connected: true,
          error: null,
        });
        callbacksRef.current.onOpen?.(event);
      };

      ws.onmessage = (event) => {
        callbacksRef.current.onMessage?.(event);
      };

      ws.onclose = (event) => {
        setState((s) => ({ ...s, readyState: WebSocket.CLOSED, connected: false }));
        callbacksRef.current.onClose?.(event);

        if (reconnect && event.code !== 1000 && reconnectAttemptRef.current < maxReconnectAttempts) {
          const delay = Math.min(
            reconnectIntervalMs * Math.pow(2, reconnectAttemptRef.current),
            MAX_RECONNECT_INTERVAL
          );
          reconnectAttemptRef.current += 1;
          setState((s) => ({
            ...s,
            reconnectAttempt: reconnectAttemptRef.current,
            error: `Reconnecting in ${Math.round(delay / 1000)}s (attempt ${reconnectAttemptRef.current}/${maxReconnectAttempts})`,
          }));
          reconnectTimeoutRef.current = setTimeout(connect, delay);
        }
      };

      ws.onerror = (event) => {
        setState((s) => ({ ...s, error: "WebSocket connection error" }));
        callbacksRef.current.onError?.(event);
      };
    } catch (e) {
      setState((s) => ({ ...s, error: `Failed to create WebSocket: ${e}` }));
    }
  }, [url, reconnect, reconnectIntervalMs, maxReconnectAttempts, enabled]);

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimeoutRef.current);
    reconnectAttemptRef.current = maxReconnectAttempts;
    wsRef.current?.close(1000, "Client disconnect");
    wsRef.current = null;
    setState((s) => ({ ...s, connected: false, readyState: WebSocket.CLOSED }));
  }, [maxReconnectAttempts]);

  const send = useCallback((data: string | ArrayBuffer | Blob | object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const payload = typeof data === "object" ? JSON.stringify(data) : data;
      wsRef.current.send(payload);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectAttemptRef.current = maxReconnectAttempts;
      wsRef.current?.close(1000, "Component unmount");
    };
  }, [connect, maxReconnectAttempts]);

  return { ...state, send, disconnect, reconnect: connect };
}
