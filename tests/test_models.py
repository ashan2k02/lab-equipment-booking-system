import pytest
from sqlalchemy.exc import IntegrityError

from app import create_app, db
from app.models import Equipment, User


@pytest.fixture
def app():
    test_app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture
def session(app):
    with app.app_context():
        yield db.session


def test_user_creation_defaults(session):
    user = User(
        username="john_doe",
        email="john@example.com",
        password="securepassword123",
    )
    session.add(user)
    session.commit()

    saved_user = User.query.filter_by(username="john_doe").first()
    assert saved_user is not None
    assert saved_user.id is not None
    assert saved_user.username == "john_doe"
    assert saved_user.email == "john@example.com"
    assert saved_user.role == User.ROLE_STUDENT
    assert saved_user.is_student is True
    assert saved_user.is_staff is False
    assert saved_user.password_hash != "securepassword123"
    assert saved_user.check_password("securepassword123") is True
    assert saved_user.check_password("wrongpassword") is False


def test_user_staff_role(session):
    staff_user = User(
        username="admin_staff",
        email="admin@example.com",
        role=User.ROLE_STAFF,
        password="adminpassword456",
    )
    session.add(staff_user)
    session.commit()

    saved_staff = User.query.filter_by(username="admin_staff").first()
    assert saved_staff.role == User.ROLE_STAFF
    assert saved_staff.is_staff is True
    assert saved_staff.is_student is False
    assert saved_staff.check_password("adminpassword456") is True


def test_user_invalid_role():
    with pytest.raises(ValueError, match="Invalid role"):
        User(
            username="bad_role_user",
            email="bad@example.com",
            role="Superuser",
            password="anypassword",
        )


def test_user_password_hashing_and_verification():
    user = User(username="hash_test", email="hash@example.com")
    user.set_password("mypassword")

    assert user.password_hash != "mypassword"
    assert user.password_hash.startswith("scrypt:") or user.password_hash.startswith(
        "pbkdf2:"
    )
    assert user.check_password("mypassword") is True
    assert user.check_password("Mypassword") is False
    assert user.check_password("") is False

    with pytest.raises(ValueError, match="Password must be a non-empty string"):
        user.set_password("")

    with pytest.raises(ValueError, match="Password must be a non-empty string"):
        user.set_password(None)


def test_user_unique_username_constraint(session):
    user1 = User(
        username="duplicate_user",
        email="user1@example.com",
        password="password123",
    )
    user2 = User(
        username="duplicate_user",
        email="user2@example.com",
        password="password456",
    )
    session.add(user1)
    session.commit()

    session.add(user2)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_user_unique_email_constraint(session):
    user1 = User(
        username="user_one",
        email="same@example.com",
        password="password123",
    )
    user2 = User(
        username="user_two",
        email="same@example.com",
        password="password456",
    )
    session.add(user1)
    session.commit()

    session.add(user2)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_flask_login_mixin_methods():
    user = User(
        username="student1",
        email="student1@example.com",
        password="pass",
    )
    user.id = 42

    assert user.is_authenticated is True
    assert user.is_active is True
    assert user.is_anonymous is False
    assert user.get_id() == "42"
    assert repr(user) == "<User student1 (Student)>"


def test_equipment_model_coexistence(session):
    equip = Equipment()
    equip.name = "Digital Oscilloscope"
    equip.category = "Electronics"
    equip.description = "100MHz 2-Channel"
    equip.status = "Available"
    session.add(equip)
    session.commit()

    saved_equip = Equipment.query.filter_by(name="Digital Oscilloscope").first()
    assert saved_equip is not None
    assert saved_equip.category == "Electronics"
    assert saved_equip.status == "Available"
