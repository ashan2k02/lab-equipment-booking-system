from datetime import date, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app import create_app, db
from app.models import Booking, Equipment, User


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


def test_staff_can_access_add_equipment_form(client):
    login_staff(client)
    response = client.get("/equipment/add")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Add Equipment" in html
    assert 'name="name"' in html
    assert 'name="category"' in html
    assert 'name="description"' in html
    assert 'name="status"' in html
    assert "Available" in html
    assert "Out of service" in html
    assert "Back to Dashboard" in html
    assert "Cancel" in html


def test_staff_dashboard_displays_add_equipment_action(client):
    login_staff(client)
    response = client.get("/staff/dashboard")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Add Lab Equipment" in html
    assert "/equipment/add" in html
    assert 'id="staff-add-equipment-btn"' in html
    assert "Lab Equipment Management" in html


def test_staff_can_successfully_create_equipment_with_flash_and_redirect(app, client):
    login_staff(client)
    response = client.post(
        "/equipment/add",
        data={
            "name": "Digital Multimeter",
            "category": "Electronics",
            "description": "High precision bench multimeter",
            "status": "Available",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Equipment added successfully." in html
    assert "Digital Multimeter" in html
    assert "Electronics" in html

    with app.app_context():
        item = Equipment.query.filter_by(name="Digital Multimeter").first()
        assert item is not None
        assert item.category == "Electronics"
        assert item.description == "High precision bench multimeter"
        assert item.status == "Available"


def test_unauthenticated_user_cannot_access_add_equipment_form(client):
    response = client.get("/equipment/add")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_unauthenticated_user_cannot_submit_add_equipment(app, client):
    response = client.post(
        "/equipment/add",
        data={
            "name": "Unauthorized Equipment",
            "category": "Hacking",
            "status": "Available",
        },
    )
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    with app.app_context():
        assert Equipment.query.filter_by(name="Unauthorized Equipment").first() is None


def test_student_cannot_access_add_equipment_form(client):
    login_student(client)
    response = client.get("/equipment/add")
    assert response.status_code == 403


def test_add_equipment_rejects_missing_category(app, client):
    login_staff(client)
    response = client.post(
        "/equipment/add",
        data={"name": "Soldering Station", "category": "", "status": "Available"},
    )
    assert response.status_code == 400
    assert "Category is required." in response.get_data(as_text=True)
    with app.app_context():
        assert Equipment.query.count() == 0


def test_add_equipment_rejects_whitespace_name(app, client):
    login_staff(client)
    response = client.post(
        "/equipment/add",
        data={"name": "   ", "category": "General", "status": "Available"},
    )
    assert response.status_code == 400
    assert "Equipment name is required." in response.get_data(as_text=True)
    with app.app_context():
        assert Equipment.query.count() == 0


def test_add_equipment_rejects_name_over_100_chars(app, client):
    login_staff(client)
    long_name = "X" * 101
    response = client.post(
        "/equipment/add",
        data={"name": long_name, "category": "General", "status": "Available"},
    )
    assert response.status_code == 400
    assert "Equipment name must be at most 100 characters." in response.get_data(as_text=True)
    with app.app_context():
        assert Equipment.query.count() == 0


def test_add_equipment_rejects_category_over_50_chars(app, client):
    login_staff(client)
    long_cat = "C" * 51
    response = client.post(
        "/equipment/add",
        data={"name": "Test Instrument", "category": long_cat, "status": "Available"},
    )
    assert response.status_code == 400
    assert "Category must be at most 50 characters." in response.get_data(as_text=True)
    with app.app_context():
        assert Equipment.query.count() == 0


def test_add_equipment_rejects_description_over_250_chars(app, client):
    login_staff(client)
    long_desc = "D" * 251
    response = client.post(
        "/equipment/add",
        data={
            "name": "Test Scope",
            "category": "Electronics",
            "description": long_desc,
            "status": "Available",
        },
    )
    assert response.status_code == 400
    assert "Description must be at most 250 characters." in response.get_data(as_text=True)
    with app.app_context():
        assert Equipment.query.count() == 0


def test_add_equipment_handles_database_integrity_error(app, client):
    login_staff(client)
    with patch.object(
        db.session,
        "commit",
        side_effect=IntegrityError("INSERT", {}, Exception("Unique violation")),
    ):
        response = client.post(
            "/equipment/add",
            data={
                "name": "Conflict Equipment",
                "category": "Conflict Category",
                "status": "Available",
            },
        )
    assert response.status_code == 400
    assert "violates database constraints" in response.get_data(as_text=True)
    with app.app_context():
        assert Equipment.query.count() == 0


def test_add_equipment_handles_database_sqlalchemy_error(app, client):
    login_staff(client)
    with patch.object(
        db.session,
        "commit",
        side_effect=SQLAlchemyError("Database connection lost"),
    ):
        response = client.post(
            "/equipment/add",
            data={
                "name": "DB Error Equipment",
                "category": "General",
                "status": "Available",
            },
        )
    assert response.status_code == 500
    assert "Failed to add equipment due to a database error." in response.get_data(as_text=True)
    with app.app_context():
        assert Equipment.query.count() == 0


def test_available_equipment_selectable_for_booking(app, client):
    login_staff(client)
    client.post(
        "/equipment/add",
        data={
            "name": "3D Printer CoreXY",
            "category": "Prototyping",
            "description": "FDM Printer with 0.4mm nozzle",
            "status": "Available",
        },
    )

    client.get("/logout")
    login_student(client)
    response = client.get("/bookings/request")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "3D Printer CoreXY" in html

    with app.app_context():
        equip = Equipment.query.filter_by(name="3D Printer CoreXY").first()
        student = User.query.filter_by(username="student1").first()
        assert equip is not None

        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        booking_res = client.post(
            "/bookings/request",
            data={
                "equipment_id": equip.id,
                "booking_date": tomorrow,
                "start_time": "10:00",
                "end_time": "12:00",
            },
        )
        assert booking_res.status_code == 302
        booking = Booking.query.filter_by(equipment_id=equip.id, user_id=student.id).first()
        assert booking is not None
        assert booking.status == Booking.STATUS_PENDING


def test_out_of_service_equipment_cannot_be_booked(app, client):
    login_staff(client)
    client.post(
        "/equipment/add",
        data={
            "name": "Broken Centrifuge",
            "category": "BioLab",
            "description": "Rotor imbalance - awaiting parts",
            "status": "Out of service",
        },
    )

    client.get("/logout")
    login_student(client)
    response = client.get("/bookings/request")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Broken Centrifuge" in html
    assert "disabled" in html

    with app.app_context():
        equip = Equipment.query.filter_by(name="Broken Centrifuge").first()
        assert equip is not None
        assert equip.status == "Out of service"

        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        booking_res = client.post(
            "/bookings/request",
            data={
                "equipment_id": equip.id,
                "booking_date": tomorrow,
                "start_time": "10:00",
                "end_time": "12:00",
            },
        )
        assert booking_res.status_code == 400
        assert "out of service" in booking_res.get_data(as_text=True).lower()
        assert Booking.query.filter_by(equipment_id=equip.id).count() == 0


def test_navbar_equipment_links(client):
    # Unauthenticated visitor does not see internal equipment links
    res_anon = client.get("/")
    assert res_anon.status_code == 200
    html_anon = res_anon.get_data(as_text=True)
    assert 'id="nav-add-equipment-link"' not in html_anon
    assert 'id="nav-catalogue-link"' not in html_anon

    # Student user sees Equipment Catalogue, but does not see Add Equipment link
    login_student(client)
    res_student = client.get("/equipment/")
    assert res_student.status_code == 200
    html_student = res_student.get_data(as_text=True)
    assert 'id="nav-catalogue-link"' in html_student
    assert 'id="nav-add-equipment-link"' not in html_student
    client.get("/logout")

    # Staff user sees both Equipment Catalogue and Add Equipment links
    login_staff(client)
    res_staff = client.get("/equipment/")
    assert res_staff.status_code == 200
    html_staff = res_staff.get_data(as_text=True)
    assert 'id="nav-catalogue-link"' in html_staff
    assert 'id="nav-add-equipment-link"' in html_staff
    assert "Add Equipment" in html_staff