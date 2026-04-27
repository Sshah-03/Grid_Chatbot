from tests.conftest import login_user, register_user


async def test_register_login_update_profile_and_search_users(client):
    alpha = await register_user(
        client,
        email="Alpha@Example.com",
        username="AlphaUser",
        full_name="Alpha One",
    )
    await register_user(
        client,
        email="beta@example.com",
        username="betauser",
        full_name="Beta Two",
    )

    assert alpha["email"] == "alpha@example.com"
    assert alpha["username"] == "alphauser"
    assert alpha["display_name"] == "alphauser"
    assert "password" not in alpha

    token, logged_in_user = await login_user(client, "alphauser")
    assert logged_in_user["email"] == "alpha@example.com"

    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "alphauser"

    updated = await client.patch(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "username": "alpha-renamed",
            "full_name": "Alpha Renamed",
            "profile_bio": "Realtime chat builder",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["username"] == "alpha-renamed"
    assert updated.json()["full_name"] == "Alpha Renamed"
    assert updated.json()["profile_bio"] == "Realtime chat builder"

    search = await client.get(
        "/auth/users/search?q=beta",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert search.status_code == 200
    assert [user["username"] for user in search.json()] == ["betauser"]


async def test_auth_rejects_duplicate_username_and_bad_password(client):
    await register_user(client, "user@example.com", "same")

    duplicate = await client.post(
        "/auth/register",
        json={
            "email": "other@example.com",
            "username": "same",
            "password": "StrongPassword123",
        },
    )
    assert duplicate.status_code == 409

    bad_login = await client.post(
        "/auth/login",
        json={"email": "same", "password": "wrong-password"},
    )
    assert bad_login.status_code == 401
