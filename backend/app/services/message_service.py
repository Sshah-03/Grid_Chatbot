from datetime import datetime
from html.parser import HTMLParser
import re
from urllib.parse import parse_qs, urljoin, urlencode, urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import LinkPreview, Message

URL_PATTERN = re.compile(
    r"(?:https?://[^\s<>()]+|www\.[^\s<>()]+|(?:youtube\.com|youtu\.be|m\.youtube\.com|music\.youtube\.com)/[^\s<>()]+)",
    re.IGNORECASE,
)
TRAILING_URL_PUNCTUATION = ".,!?;:)]}\"'"
REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36 GridChatbotLinkPreview/1.0"
    ),
}
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}


class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.title = ""
        self.metadata: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs):
        attrs_dict = {name.lower(): value for name, value in attrs if value}
        if tag.lower() == "title":
            self.in_title = True
        if tag.lower() == "meta":
            key = attrs_dict.get("property") or attrs_dict.get("name")
            content = attrs_dict.get("content")
            if key and content:
                self.metadata[key.lower()] = content.strip()

    def handle_endtag(self, tag: str):
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str):
        if self.in_title:
            self.title += data


def normalize_url(raw_url: str) -> str | None:
    url = raw_url.strip().rstrip(TRAILING_URL_PUNCTUATION)
    if not url:
        return None
    if not urlparse(url).scheme:
        url = f"https://{url}"
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return url


def extract_urls(body: str) -> list[str]:
    urls = []
    for match in URL_PATTERN.finditer(body):
        url = normalize_url(match.group(0))
        if url:
            urls.append(url)
    return list(dict.fromkeys(urls))[:5]


def is_youtube_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return host in YOUTUBE_HOSTS


def youtube_site_name(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host == "music.youtube.com":
        return "YouTube Music"
    return "YouTube"


def youtube_description(url: str, author_name: str | None) -> str:
    parsed = urlparse(url)
    video_id = parse_qs(parsed.query).get("v", [""])[0]
    if not video_id and parsed.netloc.lower() == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
    if author_name and video_id:
        return f"Video by {author_name} on YouTube"
    if author_name:
        return f"By {author_name}"
    return "YouTube video"


async def fetch_youtube_preview(client: httpx.AsyncClient, url: str) -> dict | None:
    oembed_url = "https://www.youtube.com/oembed?" + urlencode({"url": url, "format": "json"})
    response = await client.get(oembed_url, headers=REQUEST_HEADERS)
    if not response.is_success:
        return None

    try:
        data = response.json()
    except ValueError:
        return None
    title = data.get("title")
    author_name = data.get("author_name")
    thumbnail_url = data.get("thumbnail_url")
    return {
        "status": "completed",
        "title": title[:500] if title else None,
        "description": youtube_description(url, author_name)[:1000],
        "image_url": thumbnail_url[:2000] if thumbnail_url else None,
        "site_name": youtube_site_name(url),
    }


def preview_from_html(url: str, html: str) -> dict:
    parser = MetadataParser()
    parser.feed(html[:100_000])
    title = parser.metadata.get("og:title") or parser.metadata.get("twitter:title") or parser.title.strip()
    description = (
        parser.metadata.get("og:description")
        or parser.metadata.get("twitter:description")
        or parser.metadata.get("description")
    )
    image_url = parser.metadata.get("og:image") or parser.metadata.get("twitter:image")
    if image_url:
        image_url = urljoin(url, image_url)
    return {
        "title": title[:500] if title else None,
        "description": description[:1000] if description else None,
        "image_url": image_url[:2000] if image_url else None,
        "site_name": (parser.metadata.get("og:site_name") or None),
    }


async def fetch_link_preview(client: httpx.AsyncClient, url: str) -> dict:
    if is_youtube_url(url):
        youtube_preview = await fetch_youtube_preview(client, url)
        if youtube_preview:
            return youtube_preview

    response = await client.get(url, follow_redirects=True, headers=REQUEST_HEADERS)
    if not response.is_success:
        return {"status": "failed", "error": f"HTTP {response.status_code}"}
    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type:
        host = urlparse(str(response.url)).netloc or url
        return {
            "status": "completed",
            "title": host,
            "description": content_type[:1000] if content_type else None,
            "site_name": host[:255],
        }
    preview = preview_from_html(str(response.url), response.text)
    if not preview.get("title"):
        preview["title"] = urlparse(str(response.url)).netloc or url
    return {"status": "completed", **preview}


async def create_message(
    db: AsyncSession, room_id: str, user_id: str, body: str, client: httpx.AsyncClient | None = None
) -> Message:
    message = Message(room_id=room_id, user_id=user_id, body=body)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    urls = extract_urls(body)
    if urls:
        previews = []
        for url in urls:
            preview = LinkPreview(message_id=message.id, url=url, status="pending")
            if client:
                try:
                    metadata = await fetch_link_preview(client, url)
                    for key, value in metadata.items():
                        setattr(preview, key, value)
                except Exception as exc:
                    preview.status = "failed"
                    preview.error = str(exc)[:500]
            previews.append(preview)
        db.add_all(previews)
        await db.commit()
        message = await db.scalar(
            select(Message)
            .where(Message.id == message.id)
            .options(selectinload(Message.link_previews))
        )
    return message


async def get_message_history(
    db: AsyncSession, room_id: str, limit: int, before: datetime | None
) -> list[Message]:
    query = select(Message).where(Message.room_id == room_id).options(selectinload(Message.link_previews))
    if before:
        query = query.where(Message.created_at < before)
    result = await db.scalars(query.order_by(Message.created_at.desc(), Message.id.desc()).limit(limit))
    return list(result)


async def iter_message_batches(db: AsyncSession, room_id: str, batch_size: int = 500):
    offset = 0
    while True:
        rows = await db.scalars(
            select(Message)
            .where(Message.room_id == room_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
            .offset(offset)
            .limit(batch_size)
        )
        batch = list(rows)
        if not batch:
            break
        yield batch
        offset += batch_size
