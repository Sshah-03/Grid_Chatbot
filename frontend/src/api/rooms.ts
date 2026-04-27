import { apiRequest } from "./client";
import type { Message, Room } from "../types";

export function listRooms(token: string, type?: "group" | "direct") {
  const query = type ? `?type=${type}` : "";
  return apiRequest<{ items: Room[]; total: number }>(`/rooms${query}`, {}, token);
}

export function createRoom(
  token: string,
  payload: {
    name?: string;
    type: "group" | "direct";
    visibility?: "public" | "private";
    member_ids: string[];
  }
) {
  return apiRequest<Room>(
    "/rooms",
    { method: "POST", body: JSON.stringify(payload) },
    token
  );
}

export function listPublicRooms(token: string) {
  return apiRequest<{ items: Room[]; total: number }>("/rooms/public", {}, token);
}

export function getRoom(token: string, roomId: string, markRead = true) {
  return apiRequest<Room>(`/rooms/${roomId}?mark_read=${markRead}`, {}, token);
}

export function joinPublicRoom(token: string, roomId: string) {
  return apiRequest<Room>(`/rooms/${roomId}/join`, { method: "POST" }, token);
}

export function joinRoomByInvite(token: string, inviteCode: string) {
  return apiRequest<Room>(`/rooms/join/${inviteCode}`, { method: "POST" }, token);
}

export function addRoomMember(token: string, roomId: string, userId: string) {
  return apiRequest<void>(
    `/rooms/${roomId}/members`,
    { method: "POST", body: JSON.stringify({ user_id: userId }) },
    token
  );
}

export function createInvite(token: string, roomId: string) {
  return apiRequest<{ invite_code: string; invite_url: string }>(
    `/rooms/${roomId}/invite`,
    { method: "POST" },
    token
  );
}

export function getMessages(token: string, roomId: string) {
  return apiRequest<{ items: Message[]; next_cursor?: string }>(
    `/rooms/${roomId}/messages?limit=50`,
    {},
    token
  );
}
