# 💬 Grid Chatbot

Grid Chatbot is a full-stack realtime chat application built with FastAPI, React, native WebSockets, and MySQL. It supports username-based profiles, public and private group chats, direct messages, unread message indicators, invite links, optimistic message delivery states, and rich previews for public URLs including YouTube links.

The project is designed as a practical chat platform: users can register, edit their visible profile, discover other users by username, create groups, invite members, and share links that become readable preview cards inside the conversation.

## ✨ Highlights

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

## 🧰 Tech Stack

| Layer | Tools |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, lucide-react |
| Backend | FastAPI, SQLAlchemy async ORM, Pydantic |
| Database | MySQL through `asyncmy` |
| Realtime | Native WebSockets through FastAPI |
| HTTP scraping | `httpx` async client |
| Testing | Pytest, pytest-asyncio, respx |

## 🔁 Functional Flow

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

## ⚡ Messaging Flow

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

## 🗂️ Project Structure

```text
Grid_Chatbot/
├── backend/
│   ├── app/
│   │   ├── api/              REST and WebSocket route handlers
│   │   ├── core/             config, logging, security, time helpers
│   │   ├── db/               async SQLAlchemy engine/session setup
│   │   ├── models/           SQLAlchemy ORM tables
│   │   ├── schemas/          Pydantic request and response contracts
│   │   ├── services/         auth, rooms, messages, integrations
│   │   └── websockets/       in-memory WebSocket connection manager
│   ├── scripts/              MySQL setup, migration, connection helpers
│   └── tests/                backend test suite
├── frontend/
│   ├── src/
│   │   ├── api/              typed REST client functions
│   │   ├── components/       reusable React UI components
│   │   ├── context/          auth state provider
│   │   ├── hooks/            WebSocket connection hook
│   │   ├── pages/            login and chat screens
│   │   ├── types/            shared TypeScript types
│   │   └── utils/            frontend helper functions
│   ├── package.json
│   └── vite.config.ts
├── requirements.txt
├── README.md
└── .gitignore
```

## 🚀 Core Features

### 👤 User Accounts

- Register with `email`, `username`, `password`, and optional `full_name`.
- Log in with either username or email.
- Sidebar shows the signed-in username.
- Profile editor updates username, full name, and profile bio.
- User search checks username, email, full name, and display name.

### 💌 Direct Messages

- Search for another user by username.
- Start a private one-to-one chat.
- DM sidebar shows username plus full name/email information.
- DM header displays the selected user's visible profile identity.
- Direct messages use the same clean message layout as group chats.

### 👥 Public and Private Groups

- Public groups are visible to all users.
- Private groups are visible only to members.
- Group owners can add users directly by search.
- Group owners can create and copy invite links.
- Users can join groups from invite links.

### 📬 Message State

- Pending messages show while the WebSocket send is in progress.
- Sent messages replace the pending local version when the server echoes them.
- Failed messages are marked if the socket is unavailable.
- Room and DM lists show unread message counts.

### 🔗 URL and YouTube Previews

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

## 🛠️ Backend Setup

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

## 🎨 Frontend Setup

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

## 🗄️ MySQL Notes

The app uses MySQL by default. Local database connection settings are kept in ignored `.env` files, with safe examples available in the project `.env.example` files.

In development, the backend creates and updates tables automatically on startup. For production, replace this with proper Alembic migrations before deploying.

Useful scripts:

```bash
cd backend
python3 scripts/check_mysql_connection.py
python3 scripts/migrate_sqlite_to_mysql.py
```

## 🧾 Logging and Credentials

Backend logs are written to:

```text
backend/logs/app.log
```

The project logs important auth events such as registration, login, failed login, and logout. It should not log raw passwords, password hashes, bearer tokens, or WebSocket query tokens.

Credentials are stored as hashed passwords in MySQL through the `users` table. Sessions are stored separately through the session model and expire based on `TOKEN_TTL_SECONDS`.

## 🧪 Development Commands

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

## ✅ Testing

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

## 🎓 Internship Project Details

| Detail | Information |
| --- | --- |
| Project Number | 2 |
| My Role | Full Stack Developer Intern |
| Focus | Building a realtime chat application with authentication, MySQL persistence, WebSocket messaging, public/private groups, direct messages, unread indicators, and rich URL previews. |
