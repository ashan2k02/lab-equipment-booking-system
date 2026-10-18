import pytest
from sqlalchemy.exc import IntegrityError

from app import create_app, db
from app.auth import (
    permission_required,
    role_required,
    roles_required,
    staff_required,
    student_required,
)
from app.models import Equipment, User, hash_password, verify_password


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


@pytest.fixture
def student_account(app):
    with app.app_context():
        student = User(
            username="student_auth_user",
            email="student_auth@university.ac.lk",
            role=User.ROLE_STUDENT,
            password="auth_student_pass_123",
        )
        db.session.add(student)
        db.session.commit()
        return student.id


@pytest.fixture
def staff_account(app):
    with app.app_context():
        staff = User(
            username="staff_auth_user",
            email="staff_auth@university.ac.lk",
            role=User.ROLE_STAFF,
            password="auth_staff_pass_123",
        )
        db.session.add(staff)
        db.session.commit()
        return staff.id


# ============================================================================
# 1. User Model Creation & Constraints
# ============================================================================


def test_user_model_creation_and_defaults(app):
    with app.app_context():
        user = User(
            username="test_freshman",
            email="freshman@uni.ac.lk",
            password="freshman_password_99",
        )
        db.session.add(user)
        db.session.commit()

        saved = db.session.get(User, user.id)
        assert saved is not None
        assert saved.username == "test_freshman"
        assert saved.email == "freshman@uni.ac.lk"
        assert saved.role == User.ROLE_STUDENT
        assert saved.is_student is True
        assert saved.is_staff is False
        assert repr(saved) == "<User test_freshman (Student)>"

        # Password hash verification and write-only protection
        assert saved.password_hash != "freshman_password_99"
        assert saved.check_password("freshman_password_99") is True
        assert saved.check_password("wrong_password") is False
        with pytest.raises(AttributeError, match="password is not a readable attribute"):
            _ = saved.password


def test_user_model_duplicate_username_and_email_constraints(app):
    with app.app_context():
        user1 = User(
            username="unique_user",
            email="unique1@uni.ac.lk",
            password="password123",
        )
        db.session.add(user1)
        db.session.commit()

        # Duplicate username attempt
        user_dup_name = User(
            username="unique_user",
            email="different@uni.ac.lk",
            password="password123",
        )
        db.session.add(user_dup_name)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        # Duplicate email attempt
        user_dup_email = User(
            username="different_user",
            email="unique1@uni.ac.lk",
            password="password123",
        )
        db.session.add(user_dup_email)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


# ============================================================================
# 2. Student Registration Flows
# ============================================================================


def test_successful_student_registration(client, app):
    raw_pass = "student_secret_pass_2026"
    response = client.post(
        "/register",
        data={
            "username": "registered_student",
            "email": "reg_student@uni.ac.lk",
            "password": raw_pass,
            "confirm_password": raw_pass,
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Registration successful! You can now log in." in response.data
    assert b"Log In" in response.data

    with app.app_context():
        user = User.query.filter_by(username="registered_student").first()
        assert user is not None
        assert user.email == "reg_student@uni.ac.lk"
        assert user.role == User.ROLE_STUDENT
        assert user.is_student is True
        assert user.is_staff is False
        assert user.password_hash != raw_pass
        assert user.check_password(raw_pass) is True


@pytest.mark.parametrize(
    ("field_data", "expected_error"),
    [
        (
            {"username": "", "email": "a@uni.ac.lk", "password": "pass12", "confirm_password": "pass12"},
            "Username is required.",
        ),
        (
            {"username": "ab", "email": "a@uni.ac.lk", "password": "pass12", "confirm_password": "pass12"},
            "Username must be at least 3 characters long.",
        ),
        (
            {"username": "bad user!", "email": "a@uni.ac.lk", "password": "pass12", "confirm_password": "pass12"},
            "Username can only contain letters, numbers, and underscores.",
        ),
        (
            {"username": "a" * 81, "email": "a@uni.ac.lk", "password": "pass12", "confirm_password": "pass12"},
            "Username must be at most 80 characters long.",
        ),
        (
            {"username": "valid_user", "email": "", "password": "pass12", "confirm_password": "pass12"},
            "Email is required.",
        ),
        (
            {"username": "valid_user", "email": "invalid-email-format", "password": "pass12", "confirm_password": "pass12"},
            "Please provide a valid email address.",
        ),
        (
            {"username": "valid_user", "email": "user@uni.ac.lk", "password": "", "confirm_password": ""},
            "Password is required.",
        ),
        (
            {"username": "valid_user", "email": "user@uni.ac.lk", "password": "12345", "confirm_password": "12345"},
            "Password must be at least 6 characters long.",
        ),
        (
            {"username": "valid_user", "email": "user@uni.ac.lk", "password": "password123", "confirm_password": "different123"},
            "Passwords do not match.",
        ),
    ],
)
def test_invalid_registration_data(client, field_data, expected_error):
    response = client.post("/register", data=field_data)
    assert response.status_code == 400
    assert expected_error.encode("utf-8") in response.data


def test_registration_rejects_duplicate_accounts(client, student_account):
    # Attempt duplicate username
    res_name = client.post(
        "/register",
        data={
            "username": "student_auth_user",
            "email": "unique_email@uni.ac.lk",
            "password": "valid_pass_123",
            "confirm_password": "valid_pass_123",
        },
    )
    assert res_name.status_code == 400
    assert b"Username is already taken. Please choose another." in res_name.data

    # Attempt duplicate email (case-insensitive)
    res_email = client.post(
        "/register",
        data={
            "username": "unique_username",
            "email": "STUDENT_AUTH@UNIVERSITY.AC.LK",
            "password": "valid_pass_123",
            "confirm_password": "valid_pass_123",
        },
    )
    assert res_email.status_code == 400
    assert b"Email is already registered. Please use another email or log in." in res_email.data


def test_public_registration_prevents_staff_role_escalation(client, app):
    """Never trust a submitted role: public registration must strictly create Student accounts."""
    raw_pass = "security_test_password_123"
    response = client.post(
        "/register",
        data={
            "username": "hacker_attempt",
            "email": "hacker@university.ac.lk",
            "password": raw_pass,
            "confirm_password": raw_pass,
            "role": "Staff",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        user = User.query.filter_by(username="hacker_attempt").first()
        assert user is not None
        assert user.role == User.ROLE_STUDENT
        assert user.is_staff is False
        assert user.is_student is True


# ============================================================================
# 3. Password Hashing and Verification
# ============================================================================


def test_password_hashing_and_verification_suite():
    secret = "cryptographic_secret_pass_77"
    hashed = hash_password(secret)

    # Hash properties
    assert hashed != secret
    assert hashed.startswith(("scrypt:", "pbkdf2:"))

    # Salt uniqueness
    hashed_again = hash_password(secret)
    assert hashed != hashed_again

    # Verification
    assert verify_password(hashed, secret) is True
    assert verify_password(hashed_again, secret) is True
    assert verify_password(hashed, "wrong_secret") is False
    assert verify_password(None, secret) is False
    assert verify_password(hashed, None) is False


# ============================================================================
# 4. Student and Staff Login Flows
# ============================================================================


def test_successful_student_login_with_username_and_email(client, student_account):
    # Login via username
    res_user = client.post(
        "/login",
        data={"username": "student_auth_user", "password": "auth_student_pass_123"},
        follow_redirects=True,
    )
    assert res_user.status_code == 200
    assert b"Welcome back, student_auth_user!" in res_user.data
    assert b"Student" in res_user.data
    assert b"Staff Console" not in res_user.data

    # Log out
    client.get("/logout")

    # Login via email (case-insensitive)
    res_email = client.post(
        "/login",
        data={"username": "STUDENT_AUTH@UNIVERSITY.AC.LK", "password": "auth_student_pass_123"},
        follow_redirects=True,
    )
    assert res_email.status_code == 200
    assert b"Welcome back, student_auth_user!" in res_email.data


def test_successful_staff_login(client, staff_account):
    response = client.post(
        "/login",
        data={"username": "staff_auth_user", "password": "auth_staff_pass_123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Welcome back, staff_auth_user!" in response.data
    assert b"Staff" in response.data
    assert b"Staff Console" in response.data


def test_login_incorrect_passwords_and_unknown_accounts(client, student_account):
    # Unknown username
    res_unknown = client.post(
        "/login",
        data={"username": "ghost_user", "password": "any_password"},
    )
    assert res_unknown.status_code == 401
    assert b"Invalid username or password." in res_unknown.data

    # Known user, incorrect password
    res_bad_pass = client.post(
        "/login",
        data={"username": "student_auth_user", "password": "wrong_password_999"},
    )
    assert res_bad_pass.status_code == 401
    assert b"Invalid username or password." in res_bad_pass.data

    # Missing credentials
    res_no_user = client.post("/login", data={"username": "", "password": "some_password"})
    assert res_no_user.status_code == 400
    assert b"Username or email is required." in res_no_user.data

    res_no_pass = client.post("/login", data={"username": "student_auth_user", "password": ""})
    assert res_no_pass.status_code == 400
    assert b"Password is required." in res_no_pass.data


# ============================================================================
# 5. Logout and Session Handling
# ============================================================================


def test_logout_and_session_handling(client, student_account):
    # Authenticate
    client.post(
        "/login",
        data={"username": "student_auth_user", "password": "auth_student_pass_123"},
    )
    assert client.get("/dashboard").status_code == 200

    # Logout
    logout_res = client.get("/logout", follow_redirects=True)
    assert logout_res.status_code == 200
    assert b"You have been successfully logged out." in logout_res.data
    assert b"Log In" in logout_res.data

    # Accessing dashboard after logout redirects to login
    dash_res = client.get("/dashboard", follow_redirects=False)
    assert dash_res.status_code == 302
    assert "/login" in dash_res.headers["Location"]


def test_unauthenticated_logout_redirects_to_login(client):
    response = client.get("/logout", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ============================================================================
# 6. Route Authorization: Login Required & Role Restrictions
# ============================================================================


def test_authentication_required_protected_routes(client):
    # Unauthenticated visitor attempting to access dashboard
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_student_denial_on_staff_only_routes(client, student_account):
    # Log in as student
    client.post(
        "/login",
        data={"username": "student_auth_user", "password": "auth_student_pass_123"},
    )

    # Student accessing staff console receives 403 Forbidden
    response = client.get("/staff/dashboard")
    assert response.status_code == 403
    assert b"Access Denied (403 Forbidden)" in response.data


def test_authorized_staff_access(client, staff_account):
    # Log in as staff
    client.post(
        "/login",
        data={"username": "staff_auth_user", "password": "auth_staff_pass_123"},
    )

    # Staff accessing staff console is granted 200 OK
    response = client.get("/staff/dashboard")
    assert response.status_code == 200
    assert b"Staff Administration Console" in response.data
    assert b"Add, edit, and delete equipment (FR-01)" in response.data
    assert b"Review and approve or reject booking requests (FR-04)" in response.data


# ============================================================================
# 7. Integration & Architecture Coexistence
# ============================================================================


def test_user_and_equipment_model_coexistence(app):
    """Verify that User model seamlessly coexists with Equipment model in the isolated test DB."""
    with app.app_context():
        user = User(
            username="lab_tech",
            email="tech@uni.ac.lk",
            role=User.ROLE_STAFF,
            password="techpassword123",
        )
        equipment = Equipment(
            name="Spectrum Analyzer",
            category="RF Equipment",
            description="6 GHz high frequency analyzer",
            status="Available",
        )
        db.session.add(user)
        db.session.add(equipment)
        db.session.commit()

        loaded_user = User.query.filter_by(username="lab_tech").first()
        loaded_equip = Equipment.query.filter_by(name="Spectrum Analyzer").first()

        assert loaded_user is not None
        assert loaded_user.can_manage_equipment() is True
        assert loaded_equip is not None
        assert loaded_equip.status == "Available"


def test_authorization_decorators_interface(app):
    """Ensure all required authorization decorators are exported and functional."""
    assert callable(staff_required)
    assert callable(student_required)
    assert callable(role_required)
    assert callable(roles_required)
    assert callable(permission_required)
