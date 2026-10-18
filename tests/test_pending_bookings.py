from datetime import date, timedelta

import pytest

from app import create_app, db
from app.models import Booking, Equipment, User


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
def sample_data(app):
    with app.app_context():
        student = User(
            username="pending_student",
            email="pending_student@example.com",
            role=User.ROLE_STUDENT,
            password="password123",
        )
        staff = User(
            username="pending_staff",
            email="pending_staff@example.com",
            role=User.ROLE_STAFF,
            password="password123",
        )
        equipment = Equipment(
            name="Pending Booking Equipment",
            category="Electronics",
            description="Equipment for pending booking tests",
            status=Equipment.STATUS_AVAILABLE,
        )
        db.session.add_all([student, staff, equipment])
        db.session.commit()
        return {
            "student_id": student.id,
            "staff_id": staff.id,
            "equipment_id": equipment.id,
        }


def login(client, username):
    return client.post(
        "/login",
        data={"username": username, "password": "password123"},
        follow_redirects=True,
    )


def create_booking(session, sample_data, status):
    booking = Booking(
        user_id=sample_data["student_id"],
        equipment_id=sample_data["equipment_id"],
        booking_date=date.today() + timedelta(days=1),
        start_time="10:00",
        end_time="12:00",
        status=status,
    )
    session.add(booking)
    session.commit()
    return booking


def test_staff_can_view_pending_bookings_and_other_statuses_are_excluded(
    app, client, sample_data
):
    with app.app_context():
        create_booking(db.session, sample_data, Booking.STATUS_PENDING)
        create_booking(db.session, sample_data, Booking.STATUS_APPROVED)
        create_booking(db.session, sample_data, Booking.STATUS_REJECTED)
        create_booking(db.session, sample_data, Booking.STATUS_CANCELLED)

    login(client, "pending_staff")
    response = client.get("/bookings/pending")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Pending Booking Requests" in html
    assert "Pending Booking Equipment" in html
    assert "pending_student" in html
    assert html.count("Pending") >= 2
    assert "Approved" not in html
    assert "Rejected" not in html
    assert "Cancelled" not in html


def test_pending_bookings_page_shows_empty_state_for_staff(client, sample_data):
    login(client, "pending_staff")

    response = client.get("/bookings/pending")

    assert response.status_code == 200
    assert b"No Pending Booking Requests" in response.data
    assert b"no booking requests waiting for staff review" in response.data


def test_pending_bookings_page_requires_staff_access(client, sample_data):
    anonymous_response = client.get("/bookings/pending")
    assert anonymous_response.status_code == 302
    assert "/login" in anonymous_response.headers["Location"]

    login(client, "pending_student")
    student_response = client.get("/bookings/pending")
    assert student_response.status_code == 403
    assert b"Access Denied (403 Forbidden)" in student_response.data


def test_staff_dashboard_links_to_pending_bookings(client, sample_data):
    login(client, "pending_staff")

    response = client.get("/staff/dashboard")

    assert response.status_code == 200
    assert b'href="/bookings/pending"' in response.data
    assert b"View Pending Bookings" in response.data
