"""Tests for admin-only endpoints: access control (403 for non-admins), stats, and
the is_featured toggle that drives the public landing-page testimonials."""
from db.models import User


def _make_admin(client, db_session, auth_headers, uid="admin-uid"):
    """Create the local user row (via a normal request) then promote it to admin."""
    client.get("/auth/me", headers=auth_headers(uid))
    user = db_session.query(User).filter(User.supabase_uid == uid).first()
    user.role = "admin"
    db_session.commit()
    return auth_headers(uid)


def test_non_admin_gets_403_on_admin_routes(client, auth_headers):
    headers = auth_headers("regular-uid")  # get-or-created as household
    for path in ("/admin/stats", "/admin/feedback", "/admin/users", "/admin/logs"):
        resp = client.get(path, headers=headers)
        assert resp.status_code == 403, path


def test_missing_token_on_admin_returns_401(client):
    assert client.get("/admin/stats").status_code == 401


def test_admin_stats_reflects_db(client, db_session, auth_headers):
    admin = _make_admin(client, db_session, auth_headers)
    resp = client.get("/admin/stats", headers=admin)
    assert resp.status_code == 200
    body = resp.json()
    assert body["users_by_role"]["admin"] >= 1
    assert body["total_users"] == sum(body["users_by_role"].values())
    assert set(body.keys()) == {
        "users_by_role", "total_users", "total_feedback",
        "average_rating", "total_schedules", "average_savings_percent",
    }


def test_feature_toggle_controls_public_feedback(client, db_session, auth_headers):
    admin = _make_admin(client, db_session, auth_headers)

    # A regular user submits feedback.
    author = auth_headers("author-uid")
    created = client.post("/feedback", headers=author, json={"rating": 5, "message": "Tuyệt vời"})
    assert created.status_code == 201
    fid = created.json()["id"]

    # Not featured yet → absent from /feedback/public.
    public = client.get("/feedback/public").json()
    assert all(item["message"] != "Tuyệt vời" for item in public)

    # Admin features it → now present.
    patched = client.patch(f"/admin/feedback/{fid}", headers=admin, json={"is_featured": True})
    assert patched.status_code == 200
    assert patched.json()["is_featured"] is True
    public = client.get("/feedback/public").json()
    assert any(item["message"] == "Tuyệt vời" for item in public)

    # Unfeature → gone again.
    client.patch(f"/admin/feedback/{fid}", headers=admin, json={"is_featured": False})
    public = client.get("/feedback/public").json()
    assert all(item["message"] != "Tuyệt vời" for item in public)


def test_admin_feedback_rating_filter(client, db_session, auth_headers):
    admin = _make_admin(client, db_session, auth_headers)
    author = auth_headers("author2-uid")
    client.post("/feedback", headers=author, json={"rating": 3, "message": "Ổn"})
    client.post("/feedback", headers=author, json={"rating": 5, "message": "Xuất sắc"})

    resp = client.get("/admin/feedback", headers=admin, params={"rating": 5})
    assert resp.status_code == 200
    assert all(item["rating"] == 5 for item in resp.json())


def test_admin_users_lists_roles(client, db_session, auth_headers):
    admin = _make_admin(client, db_session, auth_headers)
    resp = client.get("/admin/users", headers=admin)
    assert resp.status_code == 200
    roles = {u["role"] for u in resp.json()}
    assert "admin" in roles
