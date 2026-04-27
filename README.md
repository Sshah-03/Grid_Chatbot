# Grid Chatbot

Grid Chatbot is a full-stack realtime chat application built with FastAPI, React, native WebSockets, and MySQL. It supports username-based profiles, public and private group chats, direct messages, unread message indicators, invite links, optimistic message delivery states, and rich previews for public URLs including YouTube links.

The project is designed as a practical chat platform: users can register, edit their visible profile, discover other users by username, create groups, invite members, and share links that become readable preview cards inside the conversation.

## Highlights

| Area | What It Does |
| --- | --- |
| Authentication | Register and log in with email/password; login accepts username or email. |
| Profile | Edit username, full name, and profile bio from the app sidebar. |
| Direct Messages | Search users by username, email, or full name and start one-to-one chats. |
| Groups | Create public or private groups with owner-controlled membership. |
| Invites | Copy invite links for private groups and join from pasted `/join/{code}` links. |
| Realtime Chat | WebSocket messaging with pending, sent, and failed delivery states. |
| Unread Counts | Room and DM list shows how many messages are waiting to be read. |
| Link Previews | Public URLs are scraped for title, description, image, and site name. |
| YouTube Support | YouTube links use public metadata and thumbnails for clean preview cards. |
| Persistence | MySQL stores users, sessions, rooms, messages, memberships, unread state, and link previews. |
| Logging | JSON-style backend logging with auth audit events and safe credential handling. |

## Tech Stack

| Layer | Tools |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, lucide-react |
| Backend | FastAPI, SQLAlchemy async ORM, Pydantic |
| Database | MySQL through `asyncmy` |
| Realtime | Native WebSockets through FastAPI |
| HTTP scraping | `httpx` async client |
| Testing | Pytest, pytest-asyncio, respx |

## Functional Flow

```text
User opens frontend
  -> registers or logs in with username/email and password
  -> backend creates or validates a session token
  -> frontend stores the authenticated user
  -> user selects a room or direct message
  -> frontend opens a WebSocket for that room
  -> messages are saved in MySQL
  -> backend broadcasts new messages to connected room members
  -> frontend updates message list, pending state, unread counts, and link previews
```

## Messaging Flow

```text
Send message
  -> frontend creates a temporary pending message
  -> WebSocket sends body + client_message_id
  -> backend validates token and room membership
  -> backend stores the message
  -> backend extracts public URLs from the body
  -> backend fetches metadata and stores link preview rows
  -> backend broadcasts message_created
  -> frontend replaces pending message with saved message
```

## Project Structure

```text
Grid_Chatbot/
  backend/
    app/
      api/              REST and WebSocket route handlers
      core/             config, logging, security, time helpers
      db/               async SQLAlchemy engine/session setup
      models/           SQLAlchemy ORM tables
      schemas/          Pydantic request and response contracts
      services/         business logic for auth, rooms, messages, integrations
      websockets/       in-memory WebSocket connection manager
    logs/               backend log output
    scripts/            MySQL setup, migration, and connection helpers
    tests/              backend tests
  frontend/
    src/
      api/              typed REST client functions
      components/       reusable React UI components
      context/          auth state provider
      hooks/            WebSocket connection hook
      pages/            login and chat screens
      types/            shared frontend TypeScript types
      utils/            small frontend helper functions
```

## Core Features

### User Accounts

- Register with `email`, `username`, `password`, and optional `full_name`.
- Log in with either username or email.
- Sidebar shows the signed-in username.
- Profile editor updates username, full name, and profile bio.
- User search checks username, email, full name, and display name.

### Direct Messages

- Search for another user by username.
- Start a private one-to-one chat.
- DM sidebar shows username plus full name/email information.
- DM header displays the selected user's visible profile identity.
- Direct messages use the same clean message layout as group chats.

### Public and Private Groups

- Public groups are visible to all users.
- Private groups are visible only to members.
- Group owners can add users directly by search.
- Group owners can create and copy invite links.
- Users can join groups from invite links.

### Message State

- Pending messages show while the WebSocket send is in progress.
- Sent messages replace the pending local version when the server echoes them.
- Failed messages are marked if the socket is unavailable.
- Room and DM lists show unread message counts.

### URL and YouTube Previews

When a user sends a public URL, the backend attempts to create a preview:

- Page title
- Description
- Preview image
- Site name
- Final resolved URL metadata

YouTube links receive special handling through YouTube public metadata, so pasted videos show a thumbnail and readable title rather than just a raw URL.

Supported paste styles include:

```text
https://youtube.com/watch?v=...
youtube.com/watch?v=...
https://youtu.be/...
www.github.com/owner/repo
https://example.com/article
```

## Backend Setup

From the project root:

```bash
cd backend
python3 -m venv ../venv
source ../venv/bin/activate
pip install -r ../requirements.txt
cp .env.example .env
```

Create the MySQL database and user:

```bash
mysql -u root -p < scripts/setup_mysql.sql
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

Backend runs at:

```text
http://localhost:8000
```

Interactive API docs:

```text
http://localhost:8000/docs
```

## Frontend Setup

Open a second terminal:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend runs at:

```text
http://localhost:5173
```

## Environment Variables

### Backend

File: `backend/.env`

```env
DATABASE_URL=mysql+asyncmy://chat_user:chat_pass@localhost:3306/chat_app
TOKEN_TTL_SECONDS=86400
TOKEN_SALT=change-me
HTTPX_TIMEOUT_CONNECT=3.0
HTTPX_TIMEOUT_READ=8.0
RETRY_MAX_ATTEMPTS=3
RETRY_BACKOFF_FACTOR=0.5
RETRY_JITTER_SECONDS=0.2
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/app.log
ENVIRONMENT=development
```

### Frontend

File: `frontend/.env`

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

## MySQL Notes

The app uses MySQL by default:

```env
DATABASE_URL=mysql+asyncmy://chat_user:chat_pass@localhost:3306/chat_app
```

In development, the backend creates and updates tables automatically on startup. For production, replace this with proper Alembic migrations before deploying.

Useful scripts:

```bash
cd backend
python3 scripts/check_mysql_connection.py
python3 scripts/migrate_sqlite_to_mysql.py
```

## API Overview

### Register

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "griduser",
    "password": "StrongPassword123",
    "full_name": "Grid User"
  }'
```

### Login

The `email` field accepts either email or username.

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "griduser",
    "password": "StrongPassword123"
  }'
```

### Update Profile

```bash
curl -X PATCH http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "griduser",
    "full_name": "Grid User",
    "profile_bio": "Building realtime chat flows."
  }'
```

### Search Users

```bash
curl "http://localhost:8000/auth/users/search?q=athorat" \
  -H "Authorization: Bearer $TOKEN"
```

### Create a Public Group

```bash
curl -X POST http://localhost:8000/rooms \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Grid",
    "type": "group",
    "visibility": "public",
    "member_ids": []
  }'
```

### Create a Private Group

```bash
curl -X POST http://localhost:8000/rooms \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Private Grid",
    "type": "group",
    "visibility": "private",
    "member_ids": []
  }'
```

### Create a Direct Message Room

```bash
curl -X POST http://localhost:8000/rooms \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": null,
    "type": "direct",
    "visibility": "private",
    "member_ids": ["OTHER_USER_ID"]
  }'
```

### List Rooms

```bash
curl http://localhost:8000/rooms \
  -H "Authorization: Bearer $TOKEN"
```

### List Public Groups

```bash
curl http://localhost:8000/rooms/public \
  -H "Authorization: Bearer $TOKEN"
```

### Create Invite Link

```bash
curl -X POST http://localhost:8000/rooms/$ROOM_ID/invite \
  -H "Authorization: Bearer $TOKEN"
```

### Join by Invite

```bash
curl -X POST http://localhost:8000/rooms/join/$INVITE_CODE \
  -H "Authorization: Bearer $TOKEN"
```

### Message History

```bash
curl "http://localhost:8000/rooms/$ROOM_ID/messages?limit=50" \
  -H "Authorization: Bearer $TOKEN"
```

### Export Messages

```bash
curl http://localhost:8000/rooms/$ROOM_ID/messages/export \
  -H "Authorization: Bearer $TOKEN"
```

## WebSocket Usage

Connect:

```text
ws://localhost:8000/ws/rooms/{room_id}?token={session_token}
```

Send a message:

```json
{
  "type": "message",
  "body": "Look at this video https://youtu.be/example",
  "client_message_id": "temporary-client-id"
}
```

Receive a saved message:

```json
{
  "type": "message_created",
  "message": {
    "id": "message-id",
    "room_id": "room-id",
    "user_id": "sender-id",
    "body": "Look at this video https://youtu.be/example",
    "created_at": "2026-04-27T10:00:00Z",
    "link_previews": [
      {
        "url": "https://youtu.be/example",
        "title": "Video title",
        "description": "Video by Channel on YouTube",
        "image_url": "https://...",
        "site_name": "YouTube",
        "status": "completed"
      }
    ]
  }
}
```

## Logging and Credentials

Backend logs are written to:

```text
backend/logs/app.log
```

The project logs important auth events such as registration, login, failed login, and logout. It should not log raw passwords, password hashes, bearer tokens, or WebSocket query tokens.

Credentials are stored as hashed passwords in MySQL through the `users` table. Sessions are stored separately through the session model and expire based on `TOKEN_TTL_SECONDS`.

## Development Commands

Backend:

```bash
cd backend
../venv/bin/python -m pytest
../venv/bin/python -m py_compile app/services/message_service.py
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm run dev
npm run build
npm run preview
```

## Testing

Run backend tests:

```bash
cd backend
../venv/bin/python -m pytest
```

Run frontend build verification:

```bash
cd frontend
npm run build
```

## Suggested Next Improvements

- Add Alembic migrations for production-grade schema changes.
- Add end-to-end tests for login, DM creation, group invite flow, and unread counts.
- Move more UI sections from `ChatPage.tsx` into reusable components.
- Add profile avatar support.
- Add message edit/delete support.
- Add typing indicators and online presence.
- Add a queue/background worker for link previews so very slow URLs never delay message saving.

## Current Status

The application is usable locally with:

```text
Frontend: http://localhost:5173
Backend:  http://localhost:8000
Database: MySQL
```

Start MySQL, run the backend, run the frontend, register two users, then test:

1. Update your profile username and full name.
2. Search another user by username.
3. Start a direct message.
4. Create a public group.
5. Create a private group and copy an invite link.
6. Send a normal URL and a YouTube URL to confirm preview cards appear.
# Grid_Chatbot
