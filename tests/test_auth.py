from unittest.mock import patch

import pytest
from sqlalchemy.exc import OperationalError

from app import create_app, db
from app.models import User


@pytest.fixture
def app():
    test_app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        }
    )

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


def test_get_register_page(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert b"Student Registration" in response.data
    assert b'name="username"' in response.data
    assert b'name="email"' in response.data
    assert b'name="password"' in response.data
    assert b'name="confirm_password"' in response.data


def test_register_authenticated_user_redirected(client, app):
    with app.app_context():
        user = User(
            username="logged_in_user",
            email="logged@uni.ac.lk",
            password="password",
        )
        db.session.add(user)
        db.session.commit()

    client.post(
        "/login",
        data={"username": "logged_in_user", "password": "password"},
    )
    response = client.get("/register", follow_redirects=False)
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_successful_student_registration(client, app):
    response = client.post(
        "/register",
        data={
            "username": "alice_student",
            "email": "ALICE@university.ac.lk",
            "password": "validpassword123",
            "confirm_password": "validpassword123",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Registration successful! You can now log in." in response.data

    with app.app_context():
        user = User.query.filter_by(username="alice_student").first()
        assert user is not None
        assert user.email == "alice@university.ac.lk"
        assert user.role == User.ROLE_STUDENT
        assert user.is_student is True
        assert user.is_staff is False
        assert user.password_hash != "validpassword123"
        assert user.check_password("validpassword123") is True


def test_registration_ignores_submitted_role(client, app):
    """Ensure public registration cannot be tricked into granting Staff privileges."""
    response = client.post(
        "/register",
        data={
            "username": "sneaky_user",
            "email": "sneaky@university.ac.lk",
            "password": "validpassword123",
            "confirm_password": "validpassword123",
            "role": "Staff",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        user = User.query.filter_by(username="sneaky_user").first()
        assert user is not None
        assert user.role == User.ROLE_STUDENT
        assert user.is_staff is False
        assert user.is_student is True


def test_registration_rejects_duplicate_username(client, app):
    with app.app_context():
        existing = User(
            username="existing_student",
            email="existing@university.ac.lk",
            password="securepassword",
        )
        db.session.add(existing)
        db.session.commit()

    response = client.post(
        "/register",
        data={
            "username": "existing_student",
            "email": "different@university.ac.lk",
            "password": "newpassword123",
            "confirm_password": "newpassword123",
        },
    )
    assert response.status_code == 400
    assert b"Username is already taken. Please choose another." in response.data


def test_registration_rejects_duplicate_email(client, app):
    with app.app_context():
        existing = User(
            username="user_one",
            email="same_email@university.ac.lk",
            password="securepassword",
        )
        db.session.add(existing)
        db.session.commit()

    response = client.post(
        "/register",
        data={
            "username": "user_two",
            "email": "SAME_EMAIL@university.ac.lk",
            "password": "newpassword123",
            "confirm_password": "newpassword123",
        },
    )
    assert response.status_code == 400
    assert b"Email is already registered" in response.data


@pytest.mark.parametrize(
    "form_data,expected_error",
    [
        (
            {
                "username": "",
                "email": "test@uni.ac.lk",
                "password": "password123",
                "confirm_password": "password123",
            },
            b"Username is required.",
        ),
        (
            {
                "username": "ab",
                "email": "test@uni.ac.lk",
                "password": "password123",
                "confirm_password": "password123",
            },
            b"Username must be at least 3 characters long.",
        ),
        (
            {
                "username": "invalid user!",
                "email": "test@uni.ac.lk",
                "password": "password123",
                "confirm_password": "password123",
            },
            b"Username can only contain letters, numbers, and underscores.",
        ),
        (
            {
                "username": "valid_user",
                "email": "",
                "password": "password123",
                "confirm_password": "password123",
            },
            b"Email is required.",
        ),
        (
            {
                "username": "valid_user",
                "email": "not-an-email",
                "password": "password123",
                "confirm_password": "password123",
            },
            b"Please provide a valid email address.",
        ),
        (
            {
                "username": "valid_user",
                "email": "test@uni.ac.lk",
                "password": "",
                "confirm_password": "",
            },
            b"Password is required.",
        ),
        (
            {
                "username": "valid_user",
                "email": "test@uni.ac.lk",
                "password": "123",
                "confirm_password": "123",
            },
            b"Password must be at least 6 characters long.",
        ),
        (
            {
                "username": "u" * 81,
                "email": "test@uni.ac.lk",
                "password": "password123",
                "confirm_password": "password123",
            },
            b"Username must be at most 80 characters long.",
        ),
        (
            {
                "username": "valid_user",
                "email": ("a" * 115) + "@uni.ac.lk",
                "password": "password123",
                "confirm_password": "password123",
            },
            b"Please provide a valid email address.",
        ),
        (
            {
                "username": "valid_user",
                "email": "test@uni.ac.lk",
                "password": "password123",
                "confirm_password": "mismatch456",
            },
            b"Passwords do not match.",
        ),
    ],
)
def test_registration_validation_errors(client, form_data, expected_error):
    response = client.post("/register", data=form_data)
    assert response.status_code == 400
    assert expected_error in response.data


def test_registration_database_error_handling(client):
    with patch(
        "app.auth.db.session.commit",
        side_effect=OperationalError("mock error", {}, None),
    ):
        response = client.post(
            "/register",
            data={
                "username": "db_error_user",
                "email": "dberror@university.ac.lk",
                "password": "password123",
                "confirm_password": "password123",
            },
        )
        assert response.status_code == 500
        assert b"Registration failed due to a database error" in response.data


def test_registration_integrity_error_handling(client):
    from sqlalchemy.exc import IntegrityError

    with patch(
        "app.auth.db.session.commit",
        side_effect=IntegrityError("mock integrity error", {}, None),
    ):
        response = client.post(
            "/register",
            data={
                "username": "integrity_user",
                "email": "integrity@university.ac.lk",
                "password": "password123",
                "confirm_password": "password123",
            },
        )
        assert response.status_code == 400
        assert b"A user with this username or email already exists." in response.data


@pytest.fixture
def student_user(app):
    with app.app_context():
        user = User(
            username="student_sam",
            email="sam@university.ac.lk",
            role=User.ROLE_STUDENT,
            password="sampassword123",
        )
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def staff_user(app):
    with app.app_context():
        user = User(
            username="staff_sarah",
            email="sarah@university.ac.lk",
            role=User.ROLE_STAFF,
            password="staffpassword123",
        )
        db.session.add(user)
        db.session.commit()
        return user.id


def test_login_page_renders_fields(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Account Login" in response.data
    assert b'name="username"' in response.data
    assert b'name="password"' in response.data
    assert b'name="remember"' in response.data


def test_login_validation_missing_fields(client):
    res_no_user = client.post("/login", data={"username": "", "password": "any"})
    assert res_no_user.status_code == 400
    assert b"Username or email is required." in res_no_user.data

    res_no_pass = client.post("/login", data={"username": "valid", "password": ""})
    assert res_no_pass.status_code == 400
    assert b"Password is required." in res_no_pass.data


def test_login_unknown_account_rejected(client):
    response = client.post(
        "/login",
        data={"username": "nonexistent_user", "password": "password123"},
    )
    assert response.status_code == 401
    assert b"Invalid username or password." in response.data


def test_login_incorrect_password_rejected(client, student_user):
    response = client.post(
        "/login",
        data={"username": "student_sam", "password": "wrong_password"},
    )
    assert response.status_code == 401
    assert b"Invalid username or password." in response.data


def test_login_success_with_username_and_session(client, student_user):
    response = client.post(
        "/login",
        data={"username": "student_sam", "password": "sampassword123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Welcome back, student_sam!" in response.data
    assert b"Dashboard (student_sam)" in response.data
    assert b"Student" in response.data

    # Verify protected dashboard is accessible with active session
    dash_res = client.get("/dashboard")
    assert dash_res.status_code == 200
    assert b"Hello, student_sam!" in dash_res.data
    assert b"sam@university.ac.lk" in dash_res.data


def test_login_success_with_email(client, student_user):
    response = client.post(
        "/login",
        data={"username": "SAM@UNIVERSITY.AC.LK", "password": "sampassword123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Welcome back, student_sam!" in response.data


def test_login_success_with_staff_role(client, staff_user):
    response = client.post(
        "/login",
        data={"username": "staff_sarah", "password": "staffpassword123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Welcome back, staff_sarah!" in response.data
    assert b"Staff Console" in response.data


def test_login_authenticated_user_redirected(client, student_user):
    client.post(
        "/login",
        data={"username": "student_sam", "password": "sampassword123"},
    )
    response = client.get("/login", follow_redirects=False)
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_login_remember_me_cookie(client, student_user):
    response = client.post(
        "/login",
        data={
            "username": "student_sam",
            "password": "sampassword123",
            "remember": "1",
        },
    )
    assert response.status_code == 302
    # Check that remember_token or session cookie was set
    cookie_header = response.headers.get("Set-Cookie", "")
    assert "remember_token" in cookie_header or "session=" in cookie_header


def test_login_safe_next_redirect(client, student_user):
    # Safe relative redirect
    res_safe = client.post(
        "/login?next=/dashboard",
        data={"username": "student_sam", "password": "sampassword123"},
    )
    assert res_safe.status_code == 302
    assert res_safe.headers["Location"] == "/dashboard"

    client.get("/logout")

    # Unsafe external redirect attempt should be sanitized to /dashboard
    res_unsafe = client.post(
        "/login?next=https://malicious.com/phishing",
        data={"username": "student_sam", "password": "sampassword123"},
    )
    assert res_unsafe.status_code == 302
    assert "/dashboard" in res_unsafe.headers["Location"]


def test_protected_dashboard_requires_login(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    # Following redirect should show flash message
    res_redirected = client.get("/dashboard", follow_redirects=True)
    assert res_redirected.status_code == 200
    assert b"Please log in to access this page." in res_redirected.data


def test_logout_terminates_session(client, student_user):
    client.post(
        "/login",
        data={"username": "student_sam", "password": "sampassword123"},
    )

    # Logging out
    logout_res = client.get("/logout", follow_redirects=True)
    assert logout_res.status_code == 200
    assert b"You have been successfully logged out." in logout_res.data
    assert b"Log In" in logout_res.data

    # Accessing dashboard afterwards must be blocked
    dash_res = client.get("/dashboard", follow_redirects=False)
    assert dash_res.status_code == 302
    assert "/login" in dash_res.headers["Location"]


def test_unauthenticated_logout_redirects_to_login(client):
    response = client.get("/logout", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_staff_route_accessible_by_staff_only(client, student_user, staff_user):
    # 1. Unauthenticated -> 302 to login
    anon_res = client.get("/staff/dashboard", follow_redirects=False)
    assert anon_res.status_code == 302
    assert "/login" in anon_res.headers["Location"]

    # 2. Student logged in -> 403 Forbidden
    client.post(
        "/login",
        data={"username": "student_sam", "password": "sampassword123"},
    )
    student_res = client.get("/staff/dashboard")
    assert student_res.status_code == 403

    client.get("/logout")

    # 3. Staff logged in -> 200 OK
    client.post(
        "/login",
        data={"username": "staff_sarah", "password": "staffpassword123"},
    )
    staff_res = client.get("/staff/dashboard")
    assert staff_res.status_code == 200
    assert b"Staff Administration Console" in staff_res.data


def test_load_user_helper(app):
    from app import login_manager

    with app.app_context():
        user = User(
            username="helper_user",
            email="helper@uni.ac.lk",
            password="password",
        )
        db.session.add(user)
        db.session.commit()

        # Valid ID
        loaded = login_manager._user_callback(str(user.id))
        assert loaded is not None
        assert loaded.username == "helper_user"

        # Invalid ID
        assert login_manager._user_callback("invalid_id") is None
        assert login_manager._user_callback("999999") is None

