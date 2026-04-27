import httpx

from app.services.message_service import create_message, extract_urls, fetch_link_preview
from app.services.room_service import create_room, unread_count, mark_room_read
from tests.conftest import register_user


async def test_extract_urls_accepts_public_and_youtube_url_shapes():
    urls = extract_urls(
        "Watch youtube.com/watch?v=abc, see https://youtu.be/xyz and visit www.github.com/openai."
    )

    assert urls == [
        "https://youtube.com/watch?v=abc",
        "https://youtu.be/xyz",
        "https://www.github.com/openai",
    ]


async def test_youtube_preview_uses_public_oembed_metadata():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "www.youtube.com"
        assert request.url.path == "/oembed"
        return httpx.Response(
            200,
            json={
                "title": "Demo Video",
                "author_name": "Grid Channel",
                "thumbnail_url": "https://img.youtube.com/demo.jpg",
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as preview_client:
        preview = await fetch_link_preview(preview_client, "https://youtu.be/demo")

    assert preview["status"] == "completed"
    assert preview["title"] == "Demo Video"
    assert preview["description"] == "Video by Grid Channel on YouTube"
    assert preview["image_url"] == "https://img.youtube.com/demo.jpg"
    assert preview["site_name"] == "YouTube"


async def test_generic_html_preview_reads_open_graph_metadata():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text="""
            <html>
              <head>
                <meta property="og:title" content="Article Title" />
                <meta property="og:description" content="Article summary" />
                <meta property="og:image" content="/cover.jpg" />
                <meta property="og:site_name" content="Example Site" />
              </head>
            </html>
            """,
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as preview_client:
        preview = await fetch_link_preview(preview_client, "https://example.com/post")

    assert preview["status"] == "completed"
    assert preview["title"] == "Article Title"
    assert preview["description"] == "Article summary"
    assert preview["image_url"] == "https://example.com/cover.jpg"
    assert preview["site_name"] == "Example Site"


async def test_create_message_saves_link_preview_and_unread_state(client, db_session):
    sender = await register_user(client, "sender@example.com", "sender")
    reader = await register_user(client, "reader@example.com", "reader")
    room = await create_room(
        db_session,
        "Preview Room",
        "group",
        "private",
        sender["id"],
        [reader["id"]],
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text="<title>Shared Link</title>",
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as preview_client:
        message = await create_message(
            db_session,
            room.id,
            sender["id"],
            "Read this https://example.com/shared",
            preview_client,
        )

    assert message.body == "Read this https://example.com/shared"
    assert len(message.link_previews) == 1
    assert message.link_previews[0].title == "Shared Link"
    assert await unread_count(db_session, room.id, reader["id"]) == 1

    await mark_room_read(db_session, room.id, reader["id"])
    assert await unread_count(db_session, room.id, reader["id"]) == 0
