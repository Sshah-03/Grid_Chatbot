export type User = {
  id: string;
  email: string;
  username?: string | null;
  full_name?: string | null;
  display_name?: string | null;
  profile_bio?: string | null;
  created_at?: string;
};

export type Room = {
  id: string;
  name: string | null;
  type: "group" | "direct";
  visibility: "public" | "private";
  invite_code?: string | null;
  created_by_user_id?: string;
  created_at: string;
  last_message_at?: string | null;
  unread_count?: number;
  members?: User[];
};

export type Message = {
  id: string;
  room_id: string;
  user_id: string;
  body: string;
  created_at: string;
  link_previews?: LinkPreview[];
};

export type LinkPreview = {
  url: string;
  title?: string | null;
  description?: string | null;
  image_url?: string | null;
  site_name?: string | null;
  status: string;
  error?: string | null;
};

export type FetchRun = {
  id: string;
  correlation_id: string;
  status: string;
  duration_ms: number;
  created_at: string;
};

export type FetchRunDetail = FetchRun & {
  requested_by_user_id: string;
  urls: string[];
  results: Array<{
    url: string;
    status: string;
    status_code: number | null;
    attempts: number;
    payload: unknown;
    error: string | null;
  }>;
  updated_at: string;
};
