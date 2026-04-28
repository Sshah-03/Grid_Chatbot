from tests.conftest import login_user, register_user


async def test_public_private_group_invites_direct_add_and_unread_counts(client):
    owner = await register_user(client, "owner@example.com", "owner", full_name="Owner User")
    member = await register_user(client, "member@example.com", "member", full_name="Member User")
    outsider = await register_user(client, "outsider@example.com", "outsider")
    owner_token, _ = await login_user(client, "owner")
    member_token, _ = await login_user(client, "member")
    outsider_token, _ = await login_user(client, "outsider")

    public_group = await client.post(
        "/rooms",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"name": "Public Grid", "type": "group", "visibility": "public", "member_ids": []},
    )
    assert public_group.status_code == 201, public_group.text
    public_room_id = public_group.json()["id"]

    public_rooms = await client.get(
        "/rooms/public",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert public_rooms.status_code == 200
    assert public_room_id in {room["id"] for room in public_rooms.json()["items"]}

    joined = await client.post(
        f"/rooms/{public_room_id}/join",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert joined.status_code == 200

    private_group = await client.post(
        "/rooms",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"name": "Private Grid", "type": "group", "visibility": "private", "member_ids": []},
    )
    assert private_group.status_code == 201, private_group.text
    private_payload = private_group.json()
    private_room_id = private_payload["id"]
    assert private_payload["invite_code"]

    add_member = await client.post(
        f"/rooms/{private_room_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"user_id": member["id"]},
    )
    assert add_member.status_code == 204

    rejected_add = await client.post(
        f"/rooms/{private_room_id}/members",
        headers={"Authorization": f"Bearer {member_token}"},
        json={"user_id": outsider["id"]},
    )
    assert rejected_add.status_code == 403

    invite = await client.post(
        f"/rooms/{private_room_id}/invite",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert invite.status_code == 200
    assert invite.json()["invite_url"].startswith("/join/")

    joined_by_invite = await client.post(
        f"/rooms/join/{invite.json()['invite_code']}",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert joined_by_invite.status_code == 200

    messages = await client.get(
        f"/rooms/{private_room_id}/messages",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert messages.status_code == 200
    assert messages.json()["items"] == []


async def test_direct_rooms_are_private_and_reused(client):
    current = await register_user(client, "current@example.com", "current")
    other = await register_user(client, "other@example.com", "other")
    token, _ = await login_user(client, "current")

    direct = await client.post(
        "/rooms",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": None,
            "type": "direct",
            "visibility": "private",
            "member_ids": [other["id"]],
        },
    )
    assert direct.status_code == 201, direct.text
    first_room_id = direct.json()["id"]
    assert direct.json()["name"] is None
    assert direct.json()["visibility"] == "private"

    duplicate = await client.post(
        "/rooms",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "ignored",
            "type": "direct",
            "visibility": "private",
            "member_ids": [other["id"]],
        },
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == first_room_id

    invalid = await client.post(
        "/rooms",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": None,
            "type": "direct",
            "visibility": "public",
            "member_ids": [current["id"], other["id"]],
        },
    )
    assert invalid.status_code == 400


async def test_group_member_can_delete_group_but_outsider_cannot(client):
    owner = await register_user(client, "delete-owner@example.com", "deleteowner")
    member = await register_user(client, "delete-member@example.com", "deletemember")
    outsider = await register_user(client, "delete-outsider@example.com", "deleteoutsider")
    owner_token, _ = await login_user(client, "deleteowner")
    member_token, _ = await login_user(client, "deletemember")
    outsider_token, _ = await login_user(client, "deleteoutsider")

    group = await client.post(
        "/rooms",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "name": "Temporary Group",
            "type": "group",
            "visibility": "private",
            "member_ids": [member["id"]],
        },
    )
    assert group.status_code == 201, group.text
    room_id = group.json()["id"]

    outsider_delete = await client.delete(
        f"/rooms/{room_id}",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert outsider_delete.status_code == 403

    member_delete = await client.delete(
        f"/rooms/{room_id}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert member_delete.status_code == 204

    deleted_room = await client.get(
        f"/rooms/{room_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert deleted_room.status_code == 403
