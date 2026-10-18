from datetime import date, timedelta

import pytest

from app import create_app, db
from app.models import Booking, Equipment, User


@pytest.fixture
def app():
    test_app = create_app()
    test_app.config.update(
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
def session(app):
    with app.app_context():
        yield db.session


@pytest.fixture
def sample_data(session):
    student = User(
        username="test_student",
        email="student@example.com",
        role=User.ROLE_STUDENT,
        password="password123",
    )
    staff = User(
        username="test_staff",
        email="staff@example.com",
        role=User.ROLE_STAFF,
        password="password123",
    )
    equip_available = Equipment(
        name="Digital Multimeter",
        category="Electronics",
        description="High precision multimeter",
        status=Equipment.STATUS_AVAILABLE,
    )
    equip_out_of_service = Equipment(
        name="Broken Oscilloscope",
        category="Electronics",
        description="Under repair",
        status=Equipment.STATUS_OUT_OF_SERVICE,
    )
    session.add_all([student, staff, equip_available, equip_out_of_service])
    session.commit()

    return {
        "student": student,
        "staff": staff,
        "equip_available": equip_available,
        "equip_out_of_service": equip_out_of_service,
    }


def login_user_helper(client, username, password="password123"):
    return client.post(
        "/auth/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


# ==========================================
# 1. Booking Model Unit Tests
# ==========================================


def test_booking_model_creation_and_defaults(session, sample_data):
    """Test that a new booking model is initialized with Pending status."""
    tomorrow = date.today() + timedelta(days=1)
    booking = Booking(
        user_id=sample_data["student"].id,
        equipment_id=sample_data["equip_available"].id,
        booking_date=tomorrow,
        start_time="10:00",
        end_time="12:00",
    )
    session.add(booking)
    session.commit()

    saved = db.session.get(Booking, booking.id)
    assert saved is not None
    assert saved.status == Booking.STATUS_PENDING
    assert saved.is_pending is True
    assert saved.is_approved is False
    assert saved.is_rejected is False
    assert saved.is_cancelled is False
    assert saved.duration_minutes == 120
    assert saved.user.username == "test_student"
    assert saved.equipment.name == "Digital Multimeter"
    assert "Pending" in repr(saved)


def test_booking_model_invalid_status_raises(session, sample_data):
    """Test that invalid statuses are rejected."""
    tomorrow = date.today() + timedelta(days=1)
    with pytest.raises(ValueError, match="Invalid booking status"):
        Booking(
            user_id=sample_data["student"].id,
            equipment_id=sample_data["equip_available"].id,
            booking_date=tomorrow,
            start_time="10:00",
            end_time="11:00",
            status="UnknownStatus",
        )


# ==========================================
# 2. FR-02 Route Access and Form View Tests
# ==========================================


def test_request_booking_requires_authentication(client):
    """Unauthenticated users must be redirected to login."""
    response = client.get("/bookings/request")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_request_booking_form_rendered(client, sample_data):
    """Authenticated student can view the booking form with available equipment."""
    login_user_helper(client, "test_student")
    response = client.get("/bookings/request")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Request Equipment Booking" in html
    assert "Digital Multimeter" in html
    assert "booking_date" in html
    assert "start_time" in html
    assert "end_time" in html
    assert "Initial Status: Pending" in html


# ==========================================
# 3. FR-02 Booking Submission and Pending Status
# ==========================================


def test_student_can_submit_valid_booking_request(client, sample_data, session):
    """Students can select equipment, date, start and end time.

    New valid requests are initially assigned 'Pending' status.
    """
    login_user_helper(client, "test_student")
    booking_date = (date.today() + timedelta(days=2)).isoformat()

    response = client.post(
        "/bookings/request",
        data={
            "equipment_id": sample_data["equip_available"].id,
            "booking_date": booking_date,
            "start_time": "14:00",
            "end_time": "16:00",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "submitted successfully" in html
    assert "Pending" in html

    # Verify directly in the database
    created_booking = Booking.query.filter_by(
        user_id=sample_data["student"].id
    ).first()
    assert created_booking is not None
    assert created_booking.equipment_id == sample_data["equip_available"].id
    assert created_booking.status == Booking.STATUS_PENDING
    assert created_booking.booking_date == date.fromisoformat(booking_date)
    assert created_booking.start_time.hour == 14
    assert created_booking.end_time.hour == 16


# ==========================================
# 4. Input Validation Tests
# ==========================================


def test_booking_request_missing_equipment(client, sample_data):
    """Reject request when no equipment is chosen."""
    login_user_helper(client, "test_student")
    booking_date = (date.today() + timedelta(days=1)).isoformat()

    response = client.post(
        "/bookings/request",
        data={
            "equipment_id": "",
            "booking_date": booking_date,
            "start_time": "10:00",
            "end_time": "11:00",
        },
    )
    assert response.status_code == 400
    assert "Please select an equipment item" in response.get_data(as_text=True)


def test_booking_request_out_of_service_equipment(client, sample_data):
    """Reject request for equipment marked Out of service."""
    login_user_helper(client, "test_student")
    booking_date = (date.today() + timedelta(days=1)).isoformat()

    response = client.post(
        "/bookings/request",
        data={
            "equipment_id": sample_data["equip_out_of_service"].id,
            "booking_date": booking_date,
            "start_time": "10:00",
            "end_time": "11:00",
        },
    )
    assert response.status_code == 400
    assert "out of service" in response.get_data(as_text=True)


def test_booking_request_date_in_past(client, sample_data):
    """Reject booking when date is in the past."""
    login_user_helper(client, "test_student")
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    response = client.post(
        "/bookings/request",
        data={
            "equipment_id": sample_data["equip_available"].id,
            "booking_date": yesterday,
            "start_time": "10:00",
            "end_time": "11:00",
        },
    )
    assert response.status_code == 400
    assert "past" in response.get_data(as_text=True)


def test_booking_request_end_time_before_start_time(client, sample_data):
    """Reject booking when end time is before or equal to start time."""
    login_user_helper(client, "test_student")
    booking_date = (date.today() + timedelta(days=1)).isoformat()

    response = client.post(
        "/bookings/request",
        data={
            "equipment_id": sample_data["equip_available"].id,
            "booking_date": booking_date,
            "start_time": "14:00",
            "end_time": "13:00",
        },
    )
    assert response.status_code == 400
    assert "End time must be later than start time" in response.get_data(as_text=True)


# ==========================================
# 5. User Bookings List & Detail Access Control
# ==========================================


def test_student_views_my_bookings(client, sample_data, session):
    """Student can view their own booking requests and statuses."""
    tomorrow = date.today() + timedelta(days=1)
    b = Booking(
        user_id=sample_data["student"].id,
        equipment_id=sample_data["equip_available"].id,
        booking_date=tomorrow,
        start_time="09:00",
        end_time="10:30",
        status=Booking.STATUS_PENDING,
    )
    session.add(b)
    session.commit()

    login_user_helper(client, "test_student")
    response = client.get("/bookings/my-bookings")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "My Booking Requests" in html
    assert "Digital Multimeter" in html
    assert "Pending" in html


def test_student_cannot_view_another_students_booking_detail(
    client, sample_data, session
):
    """Students are forbidden from viewing private booking details of other students."""
    other_student = User(
        username="other_student",
        email="other@example.com",
        role=User.ROLE_STUDENT,
        password="password123",
    )
    session.add(other_student)
    session.commit()

    b = Booking(
        user_id=other_student.id,
        equipment_id=sample_data["equip_available"].id,
        booking_date=date.today() + timedelta(days=1),
        start_time="09:00",
        end_time="10:30",
        status=Booking.STATUS_PENDING,
    )
    session.add(b)
    session.commit()

    login_user_helper(client, "test_student")
    response = client.get(f"/bookings/{b.id}")
    assert response.status_code == 403


def test_staff_can_view_any_booking_detail(client, sample_data, session):
    """Staff members can view details of any student's booking."""
    b = Booking(
        user_id=sample_data["student"].id,
        equipment_id=sample_data["equip_available"].id,
        booking_date=date.today() + timedelta(days=1),
        start_time="09:00",
        end_time="10:30",
        status=Booking.STATUS_PENDING,
    )
    session.add(b)
    session.commit()

    login_user_helper(client, "test_staff")
    response = client.get(f"/bookings/{b.id}")
    assert response.status_code == 200
    assert "Digital Multimeter" in response.get_data(as_text=True)
