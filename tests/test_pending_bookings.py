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


def test_staff_can_approve_pending_booking_and_status_is_persisted(
    app, client, sample_data
):
    with app.app_context():
        booking = create_booking(db.session, sample_data, Booking.STATUS_PENDING)
        booking_id = booking.id

    login(client, "pending_staff")
    response = client.post(f"/bookings/{booking_id}/approve", follow_redirects=True)

    assert response.status_code == 200
    assert b"Booking approved successfully" in response.data
    with app.app_context():
        saved_booking = db.session.get(Booking, booking_id)
        assert saved_booking.status == Booking.STATUS_APPROVED
        assert saved_booking.rejection_reason is None


def test_staff_can_reject_pending_booking_with_optional_reason(
    app, client, sample_data
):
    with app.app_context():
        booking = create_booking(db.session, sample_data, Booking.STATUS_PENDING)
        booking_id = booking.id

    login(client, "pending_staff")
    response = client.post(
        f"/bookings/{booking_id}/reject",
        data={"rejection_reason": "Equipment reserved for maintenance."},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Booking rejected successfully" in response.data
    with app.app_context():
        saved_booking = db.session.get(Booking, booking_id)
        assert saved_booking.status == Booking.STATUS_REJECTED
        assert saved_booking.rejection_reason == "Equipment reserved for maintenance."


def test_approval_rechecks_overlapping_bookings(app, client, sample_data):
    with app.app_context():
        pending_booking = create_booking(db.session, sample_data, Booking.STATUS_PENDING)
        competing_booking = Booking(
            user_id=sample_data["student_id"],
            equipment_id=sample_data["equipment_id"],
            booking_date=pending_booking.booking_date,
            start_time="11:00",
            end_time="13:00",
            status=Booking.STATUS_APPROVED,
        )
        db.session.add(competing_booking)
        db.session.commit()
        booking_id = pending_booking.id

    login(client, "pending_staff")
    response = client.post(f"/bookings/{booking_id}/approve", follow_redirects=True)

    assert response.status_code == 200
    assert b"Booking cannot be approved" in response.data
    with app.app_context():
        assert db.session.get(Booking, booking_id).status == Booking.STATUS_PENDING


def test_booking_actions_return_not_found_for_invalid_ids(client, sample_data):
    login(client, "pending_staff")

    assert client.post("/bookings/99999/approve").status_code == 404
    assert client.post("/bookings/99999/reject").status_code == 404


def test_repeated_actions_do_not_change_a_non_pending_booking(app, client, sample_data):
    with app.app_context():
        booking = create_booking(db.session, sample_data, Booking.STATUS_PENDING)
        booking_id = booking.id

    login(client, "pending_staff")
    assert client.post(f"/bookings/{booking_id}/approve").status_code == 302
    repeated_response = client.post(
        f"/bookings/{booking_id}/reject",
        data={"rejection_reason": "This must not overwrite Approved."},
        follow_redirects=True,
    )

    assert repeated_response.status_code == 200
    assert b"Only Pending bookings can be rejected" in repeated_response.data
    with app.app_context():
        saved_booking = db.session.get(Booking, booking_id)
        assert saved_booking.status == Booking.STATUS_APPROVED
        assert saved_booking.rejection_reason is None


@pytest.mark.parametrize("action", ["approve", "reject"])
def test_booking_actions_require_staff_access(app, client, sample_data, action):
    with app.app_context():
        booking = create_booking(db.session, sample_data, Booking.STATUS_PENDING)
        booking_id = booking.id

    anonymous_response = client.post(f"/bookings/{booking_id}/{action}")
    assert anonymous_response.status_code == 302
    assert "/login" in anonymous_response.headers["Location"]

    login(client, "pending_student")
    student_response = client.post(f"/bookings/{booking_id}/{action}")
    assert student_response.status_code == 403

    with app.app_context():
        assert db.session.get(Booking, booking_id).status == Booking.STATUS_PENDING


def test_student_can_see_persisted_booking_status(app, client, sample_data):
    with app.app_context():
        create_booking(db.session, sample_data, Booking.STATUS_APPROVED)

    login(client, "pending_student")
    response = client.get("/bookings/my-bookings")

    assert response.status_code == 200
    assert b"Pending Booking Equipment" in response.data
    assert b"Approved" in response.data
