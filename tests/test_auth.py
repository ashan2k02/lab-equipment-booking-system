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


def test_placeholder_login_and_logout_routes(client):
    login_res = client.get("/login")
    assert login_res.status_code == 200
    assert b"Account Login" in login_res.data

    logout_res = client.get("/logout", follow_redirects=True)
    assert logout_res.status_code == 200
    assert b"You have been logged out." in logout_res.data
