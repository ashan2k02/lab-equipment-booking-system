from datetime import date, datetime, timedelta

import pytest

import app.bookings as bookings_module
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


def test_student_cannot_override_booking_status_via_form_tampering(
    client, sample_data, session
):
    """Students cannot override or choose the booking status through form data.

    Even if a malicious user submits status='Approved', the backend must strictly
    assign 'Pending'.
    """
    login_user_helper(client, "test_student")
    booking_date = (date.today() + timedelta(days=3)).isoformat()

    response = client.post(
        "/bookings/request",
        data={
            "equipment_id": sample_data["equip_available"].id,
            "booking_date": booking_date,
            "start_time": "11:00",
            "end_time": "12:30",
            "status": "Approved",  # Attempted privilege escalation
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    # Ensure the newly saved booking has status 'Pending' and NOT 'Approved'
    created_booking = Booking.query.filter_by(
        user_id=sample_data["student"].id,
        booking_date=date.fromisoformat(booking_date),
    ).first()
    assert created_booking is not None
    assert created_booking.status == Booking.STATUS_PENDING
    assert created_booking.status != "Approved"
    assert created_booking.is_pending is True
    assert created_booking.is_approved is False


def test_booking_model_omitted_status_defaults_to_pending(session, sample_data):
    """When Booking model is instantiated without specifying status, it defaults to Pending."""
    tomorrow = date.today() + timedelta(days=1)
    booking = Booking(
        user_id=sample_data["student"].id,
        equipment_id=sample_data["equip_available"].id,
        booking_date=tomorrow,
        start_time="13:00",
        end_time="14:00",
    )
    session.add(booking)
    session.commit()

    saved = db.session.get(Booking, booking.id)
    assert saved is not None
    assert saved.status == Booking.STATUS_PENDING
    assert saved.is_pending is True


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
    assert Booking.query.count() == 0


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
    assert Booking.query.count() == 0


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
    assert Booking.query.count() == 0


def test_booking_request_equal_start_and_end_time_is_rejected(client, sample_data):
    """Reject a booking whose start and end times are identical."""
    login_user_helper(client, "test_student")
    booking_date = (date.today() + timedelta(days=1)).isoformat()

    response = client.post(
        "/bookings/request",
        data={
            "equipment_id": sample_data["equip_available"].id,
            "booking_date": booking_date,
            "start_time": "14:00",
            "end_time": "14:00",
        },
    )

    assert response.status_code == 400
    assert "End time must be later than start time" in response.get_data(as_text=True)
    assert Booking.query.count() == 0


@pytest.mark.parametrize(
    ("start_time", "end_time", "expected_status", "error_message"),
    [
        ("10:00", "10:29", 400, "Booking duration must be at least 30 minutes"),
        ("10:00", "10:30", 302, None),
        ("10:00", "14:00", 302, None),
        ("10:00", "14:01", 400, "Booking duration cannot exceed 4 hours"),
    ],
)
def test_booking_request_duration_limits(
    client,
    sample_data,
    start_time,
    end_time,
    expected_status,
    error_message,
):
    """Enforce the inclusive 30-minute to 4-hour booking-duration range."""
    login_user_helper(client, "test_student")
    booking_date = (date.today() + timedelta(days=1)).isoformat()

    response = client.post(
        "/bookings/request",
        data={
            "equipment_id": sample_data["equip_available"].id,
            "booking_date": booking_date,
            "start_time": start_time,
            "end_time": end_time,
        },
    )

    assert response.status_code == expected_status
    if error_message:
        assert error_message in response.get_data(as_text=True)
        assert Booking.query.count() == 0
    else:
        booking = Booking.query.one()
        assert booking.start_time.strftime("%H:%M") == start_time
        assert booking.end_time.strftime("%H:%M") == end_time


def test_booking_request_start_time_in_past_today_is_rejected(
    client, sample_data, monkeypatch
):
    """Use a fixed clock to reject a start time that has passed today."""

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2030, 1, 15, 12, 0, tzinfo=tz)

    monkeypatch.setattr(bookings_module, "datetime", FixedDateTime)
    login_user_helper(client, "test_student")

    response = client.post(
        "/bookings/request",
        data={
            "equipment_id": sample_data["equip_available"].id,
            "booking_date": "2030-01-15",
            "start_time": "11:30",
            "end_time": "12:30",
        },
    )

    assert response.status_code == 400
    assert "Booking cannot start in the past" in response.get_data(as_text=True)
    assert Booking.query.count() == 0


@pytest.mark.parametrize(
    ("field", "value", "error_message"),
    [
        ("booking_date", "not-a-date", "Invalid booking date format"),
        ("start_time", "not-a-time", "Invalid start time format"),
        ("end_time", "not-a-time", "Invalid end time format"),
    ],
)
def test_booking_request_malformed_date_or_time_is_rejected(
    client, sample_data, field, value, error_message
):
    """Reject malformed booking-date and time values without saving a record."""
    login_user_helper(client, "test_student")
    payload = {
        "equipment_id": sample_data["equip_available"].id,
        "booking_date": (date.today() + timedelta(days=1)).isoformat(),
        "start_time": "10:00",
        "end_time": "11:00",
    }
    payload[field] = value

    response = client.post("/bookings/request", data=payload)

    assert response.status_code == 400
    assert error_message in response.get_data(as_text=True)
    assert Booking.query.count() == 0


@pytest.mark.parametrize(
    ("equipment_id", "error_message"),
    [
        ("not-an-id", "Invalid equipment selected"),
        ("999999", "The selected equipment does not exist"),
    ],
)
def test_booking_request_invalid_or_nonexistent_equipment_is_rejected(
    client, sample_data, equipment_id, error_message
):
    """Reject invalid equipment identifiers without persisting a booking."""
    login_user_helper(client, "test_student")

    response = client.post(
        "/bookings/request",
        data={
            "equipment_id": equipment_id,
            "booking_date": (date.today() + timedelta(days=1)).isoformat(),
            "start_time": "10:00",
            "end_time": "11:00",
        },
    )

    assert response.status_code == 400
    assert error_message in response.get_data(as_text=True)
    assert Booking.query.count() == 0


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
