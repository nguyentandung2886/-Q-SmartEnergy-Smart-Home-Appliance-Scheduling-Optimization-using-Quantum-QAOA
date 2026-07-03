"""Tests for appliance CRUD endpoints."""


def test_register_seeds_12_appliances(client, auth_headers):
    headers = auth_headers("seeduser")
    response = client.get("/appliances", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 12  # HOUSEHOLD_APPLIANCES has 12 entries


def test_list_appliances_requires_auth(client):
    response = client.get("/appliances")
    assert response.status_code == 401


def test_create_appliance_returns_201(client, auth_headers):
    headers = auth_headers("createuser")
    response = client.post(
        "/appliances",
        json={"name": "Test Device", "power_w": 500, "duration_hours": 1,
              "candidate_hours": [7, 13], "is_flexible": True},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Device"
    assert data["candidate_hours"] == [7, 13]


def test_update_appliance(client, auth_headers):
    headers = auth_headers("updateuser")
    create = client.post(
        "/appliances",
        json={"name": "X", "power_w": 100, "duration_hours": 1, "candidate_hours": [], "is_flexible": False},
        headers=headers,
    )
    aid = create.json()["id"]
    update = client.put(
        f"/appliances/{aid}",
        json={"name": "X", "power_w": 200, "duration_hours": 2, "candidate_hours": [], "is_flexible": False},
        headers=headers,
    )
    assert update.status_code == 200
    assert update.json()["power_w"] == 200


def test_delete_appliance(client, auth_headers):
    headers = auth_headers("deleteuser")
    create = client.post(
        "/appliances",
        json={"name": "Y", "power_w": 50, "duration_hours": 1, "candidate_hours": [], "is_flexible": False},
        headers=headers,
    )
    aid = create.json()["id"]
    delete = client.delete(f"/appliances/{aid}", headers=headers)
    assert delete.status_code == 204
    remaining = client.get("/appliances", headers=headers).json()
    assert all(a["id"] != aid for a in remaining)


def test_create_appliance_rejects_out_of_range_candidate_hour(client, auth_headers):
    """candidate_hours outside 0-23 must 422 at create time so /optimize can't later 500
    on an unbuildable QUBO (bug #7)."""
    headers = auth_headers("badhour_create")
    response = client.post(
        "/appliances",
        json={"name": "Bad", "power_w": 500, "duration_hours": 1,
              "candidate_hours": [7, 24], "is_flexible": True},
        headers=headers,
    )
    assert response.status_code == 422


def test_update_appliance_rejects_out_of_range_candidate_hour(client, auth_headers):
    headers = auth_headers("badhour_update")
    create = client.post(
        "/appliances",
        json={"name": "Ok", "power_w": 500, "duration_hours": 1,
              "candidate_hours": [7, 13], "is_flexible": True},
        headers=headers,
    )
    aid = create.json()["id"]
    update = client.put(
        f"/appliances/{aid}",
        json={"name": "Ok", "power_w": 500, "duration_hours": 1,
              "candidate_hours": [7, -1], "is_flexible": True},
        headers=headers,
    )
    assert update.status_code == 422


def test_create_appliance_with_group_name(client, auth_headers):
    """group_name round-trips on create — used only to group multi-window fixed appliances in the UI."""
    headers = auth_headers("groupcreate")
    response = client.post(
        "/appliances",
        json={"name": "Bình nóng lạnh — Khung 1", "power_w": 2000, "duration_hours": 0.5,
              "candidate_hours": [7, 8, 9], "is_flexible": True, "group_name": "Bình nóng lạnh"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["group_name"] == "Bình nóng lạnh"


def test_create_appliance_group_name_defaults_null(client, auth_headers):
    """Omitting group_name leaves it null (single-window / legacy appliances stay ungrouped)."""
    headers = auth_headers("groupdefault")
    response = client.post(
        "/appliances",
        json={"name": "Solo", "power_w": 100, "duration_hours": 1,
              "candidate_hours": [7], "is_flexible": True},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["group_name"] is None


def test_update_appliance_group_name(client, auth_headers):
    headers = auth_headers("groupupdate")
    aid = client.post(
        "/appliances",
        json={"name": "G", "power_w": 100, "duration_hours": 1, "candidate_hours": [], "is_flexible": True},
        headers=headers,
    ).json()["id"]
    update = client.put(
        f"/appliances/{aid}",
        json={"name": "G", "power_w": 100, "duration_hours": 1, "candidate_hours": [],
              "is_flexible": True, "group_name": "Nhóm A"},
        headers=headers,
    )
    assert update.status_code == 200
    assert update.json()["group_name"] == "Nhóm A"


def test_cannot_touch_other_users_appliance(client, auth_headers):
    headers_a = auth_headers("usera")
    headers_b = auth_headers("userb")
    create = client.post(
        "/appliances",
        json={"name": "Z", "power_w": 50, "duration_hours": 1, "candidate_hours": [], "is_flexible": False},
        headers=headers_a,
    )
    aid = create.json()["id"]
    assert client.delete(f"/appliances/{aid}", headers=headers_b).status_code == 404
