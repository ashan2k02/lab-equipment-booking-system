import pytest

from app import create_app, db
from app.models import Equipment, User


@pytest.fixture
def app():
    app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}
    )
    with app.app_context():
        db.session.add(
            User(
                username="staff1",
                email="staff1@example.com",
                role=User.ROLE_STAFF,
                password="staffpass",
            )
        )
        db.session.add(
            User(
                username="student1",
                email="student1@example.com",
                role=User.ROLE_STUDENT,
                password="studentpass",
            )
        )
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, username, password):
    return client.post("/login", data={"username": username, "password": password})


def login_staff(client):
    return login(client, "staff1", "staffpass")


def login_student(client):
    return login(client, "student1", "studentpass")


def make_equipment(app, name="Arduino Kit", category="Kits", status="Available"):
    with app.app_context():
        item = Equipment(
            name=name, category=category, description="Test item", status=status
        )
        db.session.add(item)
        db.session.commit()
        return item.id


def test_staff_can_add_equipment(app, client):
    login_staff(client)
    response = client.post(
        "/equipment/add",
        data={
            "name": "Oscilloscope",
            "category": "Instruments",
            "description": "100 MHz",
            "status": "Available",
        },
    )
    assert response.status_code == 302
    with app.app_context():
        item = Equipment.query.filter_by(name="Oscilloscope").first()
        assert item is not None
        assert item.status == "Available"


def test_student_cannot_add_equipment(app, client):
    login_student(client)
    response = client.post(
        "/equipment/add",
        data={"name": "Hacked", "category": "X", "status": "Available"},
    )
    assert response.status_code == 403
    with app.app_context():
        assert Equipment.query.count() == 0


def test_anonymous_user_redirected_to_login(client):
    response = client.get("/equipment/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_student_can_view_equipment_list(app, client):
    make_equipment(app, name="Raspberry Pi Kit")
    login_student(client)
    response = client.get("/equipment/")
    assert response.status_code == 200
    assert b"Raspberry Pi Kit" in response.data


def test_category_filter_returns_only_matching_items(app, client):
    make_equipment(app, name="Arduino Kit", category="Kits")
    make_equipment(app, name="VR Headset", category="VR")
    login_student(client)
    response = client.get("/equipment/?category=VR")
    assert b"VR Headset" in response.data
    assert b"Arduino Kit" not in response.data


def test_staff_can_edit_equipment(app, client):
    equipment_id = make_equipment(app)
    login_staff(client)
    response = client.post(
        f"/equipment/{equipment_id}/edit",
        data={
            "name": "Arduino Kit v2",
            "category": "Kits",
            "description": "Updated",
            "status": "Out of service",
        },
    )
    assert response.status_code == 302
    with app.app_context():
        item = db.session.get(Equipment, equipment_id)
        assert item.name == "Arduino Kit v2"
        assert item.status == "Out of service"


def test_staff_can_delete_equipment(app, client):
    equipment_id = make_equipment(app)
    login_staff(client)
    response = client.post(f"/equipment/{equipment_id}/delete")
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Equipment, equipment_id) is None


def test_student_cannot_delete_equipment(app, client):
    equipment_id = make_equipment(app)
    login_student(client)
    response = client.post(f"/equipment/{equipment_id}/delete")
    assert response.status_code == 403
    with app.app_context():
        assert db.session.get(Equipment, equipment_id) is not None


def test_add_equipment_rejects_missing_name(app, client):
    login_staff(client)
    response = client.post(
        "/equipment/add",
        data={"name": "", "category": "Kits", "status": "Available"},
    )
    assert response.status_code == 400
    with app.app_context():
        assert Equipment.query.count() == 0


def test_add_equipment_rejects_invalid_status(app, client):
    login_staff(client)
    response = client.post(
        "/equipment/add",
        data={"name": "Drone", "category": "Misc", "status": "Broken"},
    )
    assert response.status_code == 400
    with app.app_context():
        assert Equipment.query.count() == 0