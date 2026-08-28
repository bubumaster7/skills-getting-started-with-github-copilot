import copy

import pytest
from fastapi.testclient import TestClient

import src.app as app_module


client = TestClient(app_module.app)


@pytest.fixture(autouse=True)
def reset_activities():
    original_activities = copy.deepcopy(app_module.activities)
    yield
    app_module.activities = original_activities


def test_root_redirects_to_static_index():
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


@pytest.mark.parametrize("path", ["/static/index.html", "/static/app.js", "/static/styles.css"])
def test_static_files_are_served(path):
    response = client.get(path)

    assert response.status_code == 200
    assert response.content


def test_get_activities_returns_initial_data():
    response = client.get("/activities")

    assert response.status_code == 200
    assert len(response.json()) == 9
    assert response.json()["Chess Club"]["participants"] == [
        "michael@mergington.edu",
        "daniel@mergington.edu",
    ]


def test_signup_adds_participant():
    response = client.post(
        "/activities/Art Club/signup",
        params={"email": "student@example.com"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Signed up student@example.com for Art Club"
    }
    assert "student@example.com" in client.get("/activities").json()["Art Club"]["participants"]


def test_signup_rejects_unknown_activity():
    response = client.post(
        "/activities/Unknown/signup",
        params={"email": "student@example.com"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_rejects_duplicate_participant():
    response = client.post(
        "/activities/Chess Club/signup",
        params={"email": "michael@mergington.edu"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Student is already signed up for this activity"


def test_signup_rejects_full_activity():
    activity = app_module.activities["Art Club"]
    activity["participants"] = [f"student{index}@example.com" for index in range(activity["max_participants"])]

    response = client.post(
        "/activities/Art Club/signup",
        params={"email": "new-student@example.com"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Activity is full"
    assert "new-student@example.com" not in activity["participants"]


@pytest.mark.parametrize("email", ["invalid", "student@"])
def test_signup_rejects_invalid_email(email):
    response = client.post("/activities/Art Club/signup", params={"email": email})

    assert response.status_code == 422


def test_signup_requires_email():
    response = client.post("/activities/Art Club/signup")

    assert response.status_code == 422


def test_unregister_removes_participant():
    response = client.delete(
        "/activities/Chess Club/signup",
        params={"email": "michael@mergington.edu"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Unregistered michael@mergington.edu from Chess Club"
    }
    assert "michael@mergington.edu" not in client.get("/activities").json()["Chess Club"]["participants"]


def test_unregister_rejects_unknown_activity():
    response = client.delete(
        "/activities/Unknown/signup",
        params={"email": "student@example.com"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_rejects_unknown_participant():
    response = client.delete(
        "/activities/Chess Club/signup",
        params={"email": "student@example.com"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"


def test_unregistering_twice_returns_not_found():
    params = {"email": "michael@mergington.edu"}

    assert client.delete("/activities/Chess Club/signup", params=params).status_code == 200
    response = client.delete("/activities/Chess Club/signup", params=params)

    assert response.status_code == 404


def test_unregister_requires_valid_email():
    response = client.delete(
        "/activities/Chess Club/signup",
        params={"email": "invalid"},
    )

    assert response.status_code == 422


def test_unregister_requires_email():
    response = client.delete("/activities/Chess Club/signup")

    assert response.status_code == 422