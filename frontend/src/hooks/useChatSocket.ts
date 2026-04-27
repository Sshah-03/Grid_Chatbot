import { useEffect, useRef, useState } from "react";
import type { Message } from "../types";

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";

type ChatEvent =
  | { type: "message_created"; message: Message; client_message_id?: string }
  | { type: "user_joined"; user_id: string; room_id: string; timestamp: string }
  | { type: "user_left"; user_id: string; room_id: string; timestamp: string }
  | { type: "error"; code: string; message: string }
  | { type: "pong"; timestamp: string };

export function useChatSocket(
  roomId: string | null,
  token: string | null,
  onMessage: (message: Message, clientMessageId?: string) => void
) {
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<number | null>(null);
  const attemptRef = useRef(0);
  const [status, setStatus] = useState("disconnected");
  const [lastError, setLastError] = useState<string | null>(null);

  useEffect(() => {
    if (!roomId || !token) return undefined;
    let closedByEffect = false;

    function connect() {
      setStatus(attemptRef.current ? "reconnecting" : "connecting");
      const socket = new WebSocket(`${WS_BASE_URL}/ws/rooms/${roomId}?token=${token}`);
      socketRef.current = socket;

      socket.onopen = () => {
        attemptRef.current = 0;
        setStatus("connected");
        setLastError(null);
      };

      socket.onmessage = (event) => {
        const payload = JSON.parse(event.data) as ChatEvent;
        if (payload.type === "message_created") onMessage(payload.message, payload.client_message_id);
        if (payload.type === "error") setLastError(payload.message);
      };

      socket.onclose = (event) => {
        if (closedByEffect) return;
        if (event.code === 1008) {
          setStatus("unauthorized");
          return;
        }
        attemptRef.current += 1;
        setStatus("disconnected");
        const delay = Math.min(1000 * 2 ** attemptRef.current, 10000);
        reconnectRef.current = window.setTimeout(connect, delay);
      };

      socket.onerror = () => {
        setLastError("WebSocket connection failed");
      };
    }

    connect();
    const heartbeat = window.setInterval(() => {
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ type: "ping" }));
      }
    }, 30000);

    return () => {
      closedByEffect = true;
      window.clearInterval(heartbeat);
      if (reconnectRef.current) window.clearTimeout(reconnectRef.current);
      socketRef.current?.close();
      socketRef.current = null;
      setStatus("disconnected");
    };
  }, [roomId, token, onMessage]);

  function sendMessage(body: string, clientMessageId?: string) {
    if (socketRef.current?.readyState !== WebSocket.OPEN) {
      setLastError("WebSocket is not connected");
      return false;
    }
    socketRef.current.send(JSON.stringify({ type: "message", body, client_message_id: clientMessageId }));
    return true;
  }

  return { status, lastError, sendMessage };
}
