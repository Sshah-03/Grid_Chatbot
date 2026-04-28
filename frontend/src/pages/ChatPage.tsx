import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  Copy,
  Globe,
  Lock,
  LogOut,
  MessageSquarePlus,
  Search,
  Send,
  Trash2,
  UserRoundCog,
} from "lucide-react";
import { searchUsers, updateMe } from "../api/auth";
import {
  addRoomMember,
  createInvite,
  createRoom,
  deleteRoom,
  getMessages,
  getRoom,
  joinPublicRoom,
  joinRoomByInvite,
  listPublicRooms,
  listRooms
} from "../api/rooms";
import { LinkPreviewCard } from "../components/LinkPreviewCard";
import { useAuth } from "../context/AuthContext";
import { useChatSocket } from "../hooks/useChatSocket";
import type { Message, Room, User } from "../types";

type LocalMessage = Message & {
  client_message_id?: string;
  delivery_status?: "pending" | "sent" | "failed";
};

const invitePattern = /(?:\/join\/|invite:)([a-f0-9-]{36})/i;

export function ChatPage() {
  const { token, user, logout, setUser } = useAuth();
  const [rooms, setRooms] = useState<Room[]>([]);
  const [publicRooms, setPublicRooms] = useState<Room[]>([]);
  const [activeRoom, setActiveRoom] = useState<Room | null>(null);
  const [messages, setMessages] = useState<LocalMessage[]>([]);
  const [messageBody, setMessageBody] = useState("");
  const [newRoomName, setNewRoomName] = useState("");
  const [newRoomVisibility, setNewRoomVisibility] = useState<"public" | "private">("private");
  const [directSearch, setDirectSearch] = useState("");
  const [directResults, setDirectResults] = useState<User[]>([]);
  const [profileOpen, setProfileOpen] = useState(false);
  const [profileUsername, setProfileUsername] = useState(user?.username ?? user?.display_name ?? "");
  const [profileFullName, setProfileFullName] = useState(user?.full_name ?? "");
  const [profileBio, setProfileBio] = useState(user?.profile_bio ?? "");
  const [userSearch, setUserSearch] = useState("");
  const [foundUsers, setFoundUsers] = useState<User[]>([]);
  const [currentInvite, setCurrentInvite] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const addSocketMessage = useCallback((message: Message, clientMessageId?: string) => {
    setMessages((current) => {
      if (clientMessageId) {
        const pendingIndex = current.findIndex((item) => item.client_message_id === clientMessageId);
        if (pendingIndex >= 0) {
          return current.map((item, index) =>
            index === pendingIndex
              ? { ...message, client_message_id: clientMessageId, delivery_status: "sent" }
              : item
          );
        }
      }
      if (current.some((item) => item.id === message.id)) return current;
      return [...current, { ...message, delivery_status: "sent" }];
    });
    refreshRooms().catch(() => undefined);
  }, []);

  const { status, lastError, sendMessage } = useChatSocket(
    activeRoom?.id ?? null,
    token,
    addSocketMessage
  );

  const groupedRooms = useMemo(
    () => ({
      groups: rooms.filter((room) => room.type === "group"),
      directs: rooms.filter((room) => room.type === "direct")
    }),
    [rooms]
  );

  const roomMembersById = useMemo(() => {
    const entries = activeRoom?.members?.map((member): [string, User] => [member.id, member]) ?? [];
    return new Map<string, User>(entries);
  }, [activeRoom?.members]);

  function userUsername(profile: User | null | undefined) {
    return profile?.username ?? profile?.display_name ?? profile?.email.split("@", 1)[0] ?? "";
  }

  function userFullName(profile: User | null | undefined) {
    return profile?.full_name ?? "";
  }

  function senderName(userId: string) {
    if (userId === user?.id) return userUsername(user);
    const member = roomMembersById.get(userId);
    return userUsername(member) || userId;
  }

  function messageTime(createdAt: string) {
    const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(createdAt);
    const timestamp = hasTimezone ? createdAt : `${createdAt}Z`;
    return new Date(timestamp).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function directPartner(room: Room) {
    return room.members?.find((member) => member.id !== user?.id) ?? null;
  }

  function roomTitle(room: Room | null) {
    if (!room) return "Create or select a room";
    if (room.type === "direct") {
      const partner = directPartner(room);
      return userUsername(partner) || "Direct message";
    }
    return room.name ?? "Untitled group";
  }

  function roomSubtitle(room: Room) {
    if (room.type === "direct") {
      const partner = directPartner(room);
      return userFullName(partner) || "Full name not set";
    }
    return `${room.visibility} group`;
  }

  function inviteText(inviteCodeValue: string) {
    return `${window.location.origin}/join/${inviteCodeValue}`;
  }

  async function refreshRooms() {
    if (!token) return;
    const [groups, directs, publicGroups] = await Promise.all([
      listRooms(token, "group"),
      listRooms(token, "direct"),
      listPublicRooms(token)
    ]);
    const directDetails = await Promise.all(
      directs.items.map((room) =>
        getRoom(token, room.id, false)
          .then((detail) => ({ ...detail, unread_count: room.unread_count }))
          .catch(() => room)
      )
    );
    const nextRooms = [...groups.items, ...directDetails];
    setRooms(nextRooms);
    setPublicRooms(publicGroups.items);
    setActiveRoom((current) => current ?? nextRooms[0] ?? null);
  }

  useEffect(() => {
    refreshRooms().catch((err) => setError(err.message));
  }, [token]);

  useEffect(() => {
    if (!token || !activeRoom) return;
    Promise.all([getMessages(token, activeRoom.id), getRoom(token, activeRoom.id)])
      .then(([result, room]) => {
        setMessages([...result.items].reverse().map((message) => ({ ...message, delivery_status: "sent" })));
        setActiveRoom(room);
        setCurrentInvite(room.invite_code ?? null);
        setRooms((current) =>
          current.map((item) => (item.id === room.id ? { ...item, unread_count: 0 } : item))
        );
      })
      .catch((err) => setError(err.message));
  }, [token, activeRoom?.id]);

  useEffect(() => {
    setProfileUsername(userUsername(user));
    setProfileFullName(user?.full_name ?? "");
    setProfileBio(user?.profile_bio ?? "");
  }, [user]);

  async function createGroup(event: FormEvent) {
    event.preventDefault();
    if (!token || !newRoomName.trim()) return;
    const room = await createRoom(token, {
      type: "group",
      name: newRoomName.trim(),
      visibility: newRoomVisibility,
      member_ids: []
    });
    setNewRoomName("");
    await refreshRooms();
    setActiveRoom(room);
  }

  async function saveProfile(event: FormEvent) {
    event.preventDefault();
    if (!token || !profileUsername.trim()) return;
    const updated = await updateMe(token, {
      username: profileUsername.trim(),
      full_name: profileFullName.trim() || null,
      profile_bio: profileBio.trim() || null
    });
    setUser(updated);
    setProfileOpen(false);
  }

  async function findUsers(event: FormEvent) {
    event.preventDefault();
    if (!token || !userSearch.trim()) return;
    setFoundUsers(await searchUsers(token, userSearch.trim()));
  }

  async function findDirectUsers(event: FormEvent) {
    event.preventDefault();
    if (!token || !directSearch.trim()) return;
    setDirectResults(await searchUsers(token, directSearch.trim()));
  }

  async function addFoundUser(userId: string) {
    if (!token || !activeRoom) return;
    await addRoomMember(token, activeRoom.id, userId);
    setFoundUsers((current) => current.filter((item) => item.id !== userId));
    setActiveRoom(await getRoom(token, activeRoom.id));
  }

  async function joinGroup(room: Room) {
    if (!token) return;
    const joined = await joinPublicRoom(token, room.id);
    await refreshRooms();
    setActiveRoom(joined);
  }

  async function copyInviteLink() {
    if (!token || !activeRoom) return;
    const inviteCodeValue = currentInvite ?? (await createInvite(token, activeRoom.id)).invite_code;
    setCurrentInvite(inviteCodeValue);
    await navigator.clipboard.writeText(inviteText(inviteCodeValue));
  }

  async function deleteActiveGroup() {
    if (!token || !activeRoom || activeRoom.type !== "group") return;
    const confirmed = window.confirm(`Delete "${roomTitle(activeRoom)}"? This cannot be undone.`);
    if (!confirmed) return;
    await deleteRoom(token, activeRoom.id);
    setMessages([]);
    setCurrentInvite(null);
    setActiveRoom(null);
    await refreshRooms();
  }

  async function joinInviteFromMessage(inviteCodeValue: string) {
    if (!token) return;
    const joined = await joinRoomByInvite(token, inviteCodeValue);
    await refreshRooms();
    setActiveRoom(joined);
  }

  function renderMessageBody(body: string) {
    const match = body.match(invitePattern);
    if (!match) return body;
    const inviteCodeValue = match[1];
    const before = body.slice(0, match.index);
    const after = body.slice((match.index ?? 0) + match[0].length);
    return (
      <>
        {before}
        <button className="inline-invite" onClick={() => joinInviteFromMessage(inviteCodeValue)}>
          Join private group
        </button>
        <code className="inline-code">/join/{inviteCodeValue}</code>
        {after}
      </>
    );
  }

  async function startDirectChat(otherUserId: string) {
    if (!token) return;
    const room = await createRoom(token, {
      type: "direct",
      member_ids: [otherUserId]
    });
    setDirectSearch("");
    setDirectResults([]);
    await refreshRooms();
    setActiveRoom(room);
  }

  function submitMessage(event: FormEvent) {
    event.preventDefault();
    if (!messageBody.trim() || !activeRoom || !user) return;
    const body = messageBody.trim();
    const clientMessageId = crypto.randomUUID();
    const pendingMessage: LocalMessage = {
      id: clientMessageId,
      client_message_id: clientMessageId,
      room_id: activeRoom.id,
      user_id: user.id,
      body,
      created_at: new Date().toISOString(),
      delivery_status: "pending"
    };
    setMessages((current) => [...current, pendingMessage]);
    const queued = sendMessage(body, clientMessageId);
    if (!queued) {
      setMessages((current) =>
        current.map((message) =>
          message.client_message_id === clientMessageId
            ? { ...message, delivery_status: "failed" }
            : message
        )
      );
    }
    setMessageBody("");
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand-row">
          <div>
            <p className="eyebrow">Signed in as</p>
            <strong>{userUsername(user)}</strong>
          </div>
          <button className="icon-button" onClick={logout} title="Logout">
            <LogOut size={18} />
          </button>
        </div>

        <button className="profile-toggle" onClick={() => setProfileOpen((open) => !open)}>
          <UserRoundCog size={18} />
          Profile
        </button>
        {profileOpen && (
          <form className="profile-form" onSubmit={saveProfile}>
            <input
              value={profileUsername}
              onChange={(event) => setProfileUsername(event.target.value)}
              placeholder="Username"
              required
            />
            <input
              value={profileFullName}
              onChange={(event) => setProfileFullName(event.target.value)}
              placeholder="Full name"
            />
            <input
              value={profileBio}
              onChange={(event) => setProfileBio(event.target.value)}
              placeholder="Profile bio"
            />
            <button className="primary">Save profile</button>
          </form>
        )}

        <form className="compact-form group-create" onSubmit={createGroup}>
          <input
            value={newRoomName}
            onChange={(event) => setNewRoomName(event.target.value)}
            placeholder="New group room"
          />
          <div className="visibility-toggle">
            <button
              type="button"
              className={newRoomVisibility === "private" ? "active" : ""}
              onClick={() => setNewRoomVisibility("private")}
              title="Private group"
            >
              <Lock size={16} />
              Private
            </button>
            <button
              type="button"
              className={newRoomVisibility === "public" ? "active" : ""}
              onClick={() => setNewRoomVisibility("public")}
              title="Public group"
            >
              <Globe size={16} />
              Public
            </button>
          </div>
          <button title="Create room">
            <MessageSquarePlus size={18} />
          </button>
        </form>

        <form className="compact-form" onSubmit={findDirectUsers}>
          <input
            value={directSearch}
            onChange={(event) => setDirectSearch(event.target.value)}
            placeholder="Search username for DM"
          />
          <button title="Search users for direct message">
            <Search size={18} />
          </button>
        </form>
        {!!directResults.length && (
          <div className="search-results sidebar-results">
            {directResults.map((found) => (
              <button key={found.id} onClick={() => startDirectChat(found.id)}>
                <span>{userUsername(found)}</span>
                <small>{userFullName(found) || "Full name not set"}</small>
              </button>
            ))}
          </div>
        )}

        <RoomSection
          title="Rooms"
          rooms={groupedRooms.groups}
          active={activeRoom}
          onSelect={setActiveRoom}
          getTitle={roomTitle}
          getSubtitle={roomSubtitle}
        />
        <RoomSection
          title="Direct"
          rooms={groupedRooms.directs}
          active={activeRoom}
          onSelect={setActiveRoom}
          getTitle={roomTitle}
          getSubtitle={roomSubtitle}
        />
        <RoomSection
          title="Public groups"
          rooms={publicRooms}
          active={activeRoom}
          onSelect={joinGroup}
          getTitle={roomTitle}
          getSubtitle={roomSubtitle}
          actionLabel="Join"
        />
      </aside>

      <section className="chat-panel">
        <header className="panel-header">
          <div>
            <p className="eyebrow">{activeRoom?.type ?? "No room"}</p>
            <h1>{roomTitle(activeRoom)}</h1>
            {activeRoom && (
              <small>
                {roomSubtitle(activeRoom)}
              </small>
            )}
          </div>
          <div className="panel-actions">
            {activeRoom?.type === "group" && (
              <button className="danger-button" onClick={deleteActiveGroup} title="Delete group">
                <Trash2 size={17} />
                Delete group
              </button>
            )}
            <span className={`status ${status}`}>{status}</span>
          </div>
        </header>

        {activeRoom?.type === "group" && (
          <section className="group-tools">
            <form className="compact-form" onSubmit={findUsers}>
              <input
                value={userSearch}
                onChange={(event) => setUserSearch(event.target.value)}
                placeholder="Search users by name or email"
              />
              <button title="Search users">
                <Search size={18} />
              </button>
            </form>
            <button className="icon-text" onClick={copyInviteLink} title="Copy invite link">
              <Copy size={18} />
              Copy link
            </button>
            {!!foundUsers.length && (
              <div className="search-results">
                {foundUsers.map((found) => (
                  <div key={found.id} className="search-result-row">
                    <span>{userUsername(found)}</span>
                    <small>{userFullName(found) || "Full name not set"}</small>
                    <button onClick={() => addFoundUser(found.id)}>Add</button>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        <div className="messages">
          {messages.map((message) => (
            <article
              key={message.id}
              className={[
                message.user_id === user?.id ? "message mine" : "message",
                message.delivery_status === "pending" ? "pending" : "",
                message.delivery_status === "failed" ? "failed" : ""
              ].filter(Boolean).join(" ")}
            >
              <small>{senderName(message.user_id)}</small>
              <p>{renderMessageBody(message.body)}</p>
              {!!message.link_previews?.length && (
                <div className="link-previews">
                  {message.link_previews.map((preview) => (
                    <LinkPreviewCard key={preview.url} preview={preview} />
                  ))}
                </div>
              )}
              <time>
                {messageTime(message.created_at)}
                {message.delivery_status === "pending" && " · pending"}
                {message.delivery_status === "failed" && " · failed"}
              </time>
            </article>
          ))}
          {!messages.length && <p className="muted">No messages yet.</p>}
        </div>

        {(error || lastError) && <p className="error">{error || lastError}</p>}
        <form className="message-form" onSubmit={submitMessage}>
          <input
            value={messageBody}
            onChange={(event) => setMessageBody(event.target.value)}
            placeholder="Write a message"
            disabled={!activeRoom}
          />
          <button className="send-button" disabled={!activeRoom} title="Send message" aria-label="Send message">
            <Send size={18} />
          </button>
        </form>
      </section>

    </main>
  );
}

function RoomSection({
  title,
  rooms,
  active,
  onSelect,
  getTitle,
  getSubtitle,
  actionLabel
}: {
  title: string;
  rooms: Room[];
  active: Room | null;
  onSelect: (room: Room) => void;
  getTitle: (room: Room) => string;
  getSubtitle: (room: Room) => string;
  actionLabel?: string;
}) {
  return (
    <section className="room-section">
      <h2>{title}</h2>
      {rooms.map((room) => (
        <button
          key={room.id}
          className={active?.id === room.id ? "room active" : "room"}
          onClick={() => onSelect(room)}
        >
          <span>{getTitle(room)}</span>
          {!!room.unread_count && <strong className="unread-badge">{room.unread_count}</strong>}
          <small>{actionLabel ?? getSubtitle(room)}</small>
        </button>
      ))}
    </section>
  );
}
