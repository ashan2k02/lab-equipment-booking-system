import pytest

from app import create_app, db
from app.models import User, hash_password, verify_password


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


def test_hash_password_utility():
    plaintext = "super_secure_pass_123"
    hashed = hash_password(plaintext)

    assert hashed != plaintext
    assert hashed.startswith(("scrypt:", "pbkdf2:"))
    assert verify_password(hashed, plaintext) is True
    assert verify_password(hashed, "wrong_password") is False


def test_hash_password_salt_uniqueness():
    """Ensure two hashes of the identical password generate different salt hashes."""
    plaintext = "identical_password"
    hash1 = hash_password(plaintext)
    hash2 = hash_password(plaintext)

    assert hash1 != hash2
    assert verify_password(hash1, plaintext) is True
    assert verify_password(hash2, plaintext) is True


def test_hash_password_invalid_inputs():
    with pytest.raises(ValueError, match="Password must be a non-empty string"):
        hash_password("")

    with pytest.raises(ValueError, match="Password must be a non-empty string"):
        hash_password(None)

    with pytest.raises(ValueError, match="Password must be a non-empty string"):
        hash_password(12345)


def test_verify_password_edge_cases():
    valid_hash = hash_password("test_pass")

    assert verify_password(None, "test_pass") is False
    assert verify_password(valid_hash, None) is False
    assert verify_password("", "test_pass") is False
    assert verify_password(valid_hash, "") is False
    assert verify_password(None, None) is False


def test_user_password_property_write_only():
    user = User(username="prop_user", email="prop@uni.ac.lk")
    user.password = "property_password"

    # Verify write succeeded
    assert user.password_hash is not None
    assert user.password_hash != "property_password"
    assert user.check_password("property_password") is True

    # Verify read is prohibited
    with pytest.raises(AttributeError, match="password is not a readable attribute"):
        _ = user.password


def test_registration_and_login_hash_compatibility(client, app):
    """Verify that registration stores a hash and login successfully verifies against it."""
    plaintext = "student_login_pass_789"

    # 1. Register student
    reg_res = client.post(
        "/register",
        data={
            "username": "hash_student",
            "email": "hash_student@uni.ac.lk",
            "password": plaintext,
            "confirm_password": plaintext,
        },
        follow_redirects=True,
    )
    assert reg_res.status_code == 200

    # 2. Inspect database record: verify only hash is stored
    with app.app_context():
        user = User.query.filter_by(username="hash_student").first()
        assert user is not None
        assert user.password_hash != plaintext
        assert plaintext not in user.password_hash
        assert user.check_password(plaintext) is True

    # 3. Login with correct password
    login_success = client.post(
        "/login",
        data={"username": "hash_student", "password": plaintext},
        follow_redirects=True,
    )
    assert login_success.status_code == 200
    assert b"Welcome back, hash_student!" in login_success.data

    # 4. Login with incorrect password fails
    client.get("/logout")
    login_failure = client.post(
        "/login",
        data={"username": "hash_student", "password": "wrong_plain_text"},
    )
    assert login_failure.status_code == 401
    assert b"Invalid username or password." in login_failure.data
