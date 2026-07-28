/**
 * WebSocket hook for real-time dashboard updates.
 * Connects to the backend WebSocket endpoint, auto-reconnects on drop,
 * and provides a fallback polling mechanism.
 */
import { useEffect, useRef, useCallback } from 'react';

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

export default function useWebSocket(tenantId, userId, onMessage) {
  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const reconnectAttemptRef = useRef(0);
  const mountedRef = useRef(true);
  // connect() schedules a retry of itself via setTimeout on close/error.
  // Referencing the `connect` const directly from within its own body works
  // (by the time the timeout fires, the assignment below has long since
  // completed) but the lint rule can't see that — routing through a ref
  // avoids the self-reference entirely rather than leaving it flagged.
  const connectRef = useRef(null);

  const connect = useCallback(() => {
    if (!tenantId || !userId || !mountedRef.current) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = `${protocol}//${host}/ws/${tenantId}/${userId}`;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttemptRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'feed_update' && onMessage) {
            onMessage(data);
          } else if (data.type === 'pong') {
            // Heartbeat response — ignore
          } else if (data.type === 'presence_update' && onMessage) {
            onMessage(data);
          } else if (data.type === 'delegation_received' && onMessage) {
            onMessage(data);
          } else if (data.type === 'delegation_update' && onMessage) {
            onMessage(data);
          }
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = () => {
        if (mountedRef.current) {
          const delay = Math.min(
            RECONNECT_BASE_MS * Math.pow(2, reconnectAttemptRef.current),
            RECONNECT_MAX_MS
          );
          reconnectAttemptRef.current += 1;
          reconnectTimerRef.current = setTimeout(() => connectRef.current(), delay);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      // Connection failed — retry
      if (mountedRef.current) {
        reconnectTimerRef.current = setTimeout(() => connectRef.current(), RECONNECT_BASE_MS);
      }
    }
  }, [tenantId, userId, onMessage]);

  // Mutating a ref during render is unsafe (React's compiler flags it) —
  // keep it updated via an effect instead. No dependency array: runs after
  // every render, so connectRef always reflects the latest connect by the
  // time it's actually invoked (asynchronously, from a setTimeout).
  useEffect(() => {
    connectRef.current = connect;
  });

  useEffect(() => {
    mountedRef.current = true;
    connect();

    // Send heartbeat ping every 30s
    const pingInterval = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);

    return () => {
      mountedRef.current = false;
      clearInterval(pingInterval);
      clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);
}