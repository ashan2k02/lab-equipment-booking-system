from datetime import date, timedelta

import pytest

from app import create_app, db
from app.models import Booking, Equipment, User


@pytest.fixture
def app():
    """Create and configure a clean Flask application instance for integration testing."""
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
    """Test client for issuing HTTP requests."""
    return app.test_client()


@pytest.fixture
def student_user(app):
    """Fixture providing a registered student user account."""
    with app.app_context():
        user = User(
            username="student_integ_user",
            email="student_integ@university.ac.lk",
            role=User.ROLE_STUDENT,
            password="secure_password_123",
        )
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def available_equipment(app):
    """Fixture providing an available equipment item."""
    with app.app_context():
        equip = Equipment(
            name="Digital Multimeter Fluke 87V",
            category="Electronics",
            description="True-RMS industrial multimeter",
            status=Equipment.STATUS_AVAILABLE,
        )
        db.session.add(equip)
        db.session.commit()
        return equip.id


def login_student(client, username="student_integ_user", password="secure_password_123"):
    """Helper function to log in the student test user."""
    return client.post(
        "/auth/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


# ============================================================================
# Requirement 1: Authenticated student can submit a booking request
# ============================================================================


def test_authenticated_student_can_submit_booking_request(
    app, client, student_user, available_equipment
):
    """An authenticated student can successfully submit a booking request with

    equipment, booking date, start time, and end time.
    """
    login_student(client)
    target_date = (date.today() + timedelta(days=2)).isoformat()

    response = client.post(
        "/bookings/request",
        data={
            "equipment_id": available_equipment,
            "booking_date": target_date,
            "start_time": "10:00",
            "end_time": "12:00",
        },
        follow_redirects=True,
    )

    # Verifies redirect to my-bookings with success message
    assert response.status_code == 200
    content = response.get_data(as_text=True)
    assert "Digital Multimeter Fluke 87V" in content
    assert "submitted successfully" in content

    # Verifies database persistence with correct attributes
    with app.app_context():
        booking = Booking.query.filter_by(user_id=student_user).first()
        assert booking is not None
        assert booking.equipment_id == available_equipment
        assert booking.booking_date == date.fromisoformat(target_date)
        assert booking.start_time.hour == 10
        assert booking.start_time.minute == 0
        assert booking.end_time.hour == 12
        assert booking.end_time.minute == 0


# ============================================================================
# Requirement 2: Required fields are validated
# ============================================================================


@pytest.mark.parametrize(
    "missing_field, payload, expected_error_snippet",
    [
        (
            "equipment_id",
            {
                "equipment_id": "",
                "booking_date": (date.today() + timedelta(days=1)).isoformat(),
                "start_time": "09:00",
                "end_time": "11:00",
            },
            "Please select an equipment item",
        ),
        (
            "booking_date",
            {
                "equipment_id": "1",
                "booking_date": "",
                "start_time": "09:00",
                "end_time": "11:00",
            },
            "Booking date is required",
        ),
        (
            "start_time",
            {
                "equipment_id": "1",
                "booking_date": (date.today() + timedelta(days=1)).isoformat(),
                "start_time": "",
                "end_time": "11:00",
            },
            "Start time is required",
        ),
        (
            "end_time",
            {
                "equipment_id": "1",
                "booking_date": (date.today() + timedelta(days=1)).isoformat(),
                "start_time": "09:00",
                "end_time": "",
            },
            "End time is required",
        ),
    ],
)
def test_required_fields_validation_and_no_record_saved(
    app, client, student_user, available_equipment, missing_field, payload, expected_error_snippet
):
    """Submissions missing any required field must be rejected with HTTP 400,

    display an informative error message, and write nothing to the database.
    """
    login_student(client)

    # Use valid equipment_id if this test is testing a different missing field
    if payload["equipment_id"] == "1":
        payload["equipment_id"] = str(available_equipment)

    response = client.post(
        "/bookings/request",
        data=payload,
    )

    assert response.status_code == 400
    assert expected_error_snippet in response.get_data(as_text=True)

    # Database must remain untouched
    with app.app_context():
        assert Booking.query.count() == 0


def test_empty_form_submission_rejected(app, client, student_user):
    """Submitting completely empty form data is rejected and saves no booking."""
    login_student(client)

    response = client.post("/bookings/request", data={})
    assert response.status_code == 400

    with app.app_context():
        assert Booking.query.count() == 0


# ============================================================================
# Requirement 3: Valid new booking is saved in DB with 'Pending' status
# ============================================================================


def test_valid_booking_saved_with_pending_status(
    app, client, student_user, available_equipment
):
    """A valid new booking request must strictly be saved with its status set to 'Pending'."""
    login_student(client)
    target_date = (date.today() + timedelta(days=3)).isoformat()

    response = client.post(
        "/bookings/request",
        data={
            "equipment_id": available_equipment,
            "booking_date": target_date,
            "start_time": "13:00",
            "end_time": "15:00",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        booking = Booking.query.filter_by(user_id=student_user).first()
        assert booking is not None
        assert booking.status == Booking.STATUS_PENDING
        assert booking.status == "Pending"
        assert booking.is_pending is True
        assert booking.is_approved is False
        assert booking.is_rejected is False


# ============================================================================
# Requirement 4: Student cannot set an arbitrary booking status through form
# ============================================================================


@pytest.mark.parametrize(
    "tampered_status",
    [
        "Approved",
        "approved",
        "Active",
        "Confirmed",
        "Rejected",
        "ArbitraryStatus",
    ],
)
def test_student_cannot_set_arbitrary_status_via_form_tampering(
    app, client, student_user, available_equipment, tampered_status
):
    """Students cannot choose or override booking status via submitted form data.

    Any submitted 'status' value must be ignored and the record saved as 'Pending'.
    """
    login_student(client)
    target_date = (date.today() + timedelta(days=4)).isoformat()

    response = client.post(
        "/bookings/request",
        data={
            "equipment_id": available_equipment,
            "booking_date": target_date,
            "start_time": "14:00",
            "end_time": "16:00",
            "status": tampered_status,
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        booking = Booking.query.filter_by(
            user_id=student_user,
            booking_date=date.fromisoformat(target_date),
        ).first()

        assert booking is not None
        # Enforce that tampered status is strictly ignored and Pending is assigned
        assert booking.status == Booking.STATUS_PENDING
        assert booking.status != tampered_status
        assert booking.is_pending is True


# ============================================================================
# Requirement 5: Unauthenticated users cannot submit booking requests
# ============================================================================


def test_unauthenticated_user_cannot_access_booking_form(app, client):
    """Unauthenticated GET request to /bookings/request redirects to login."""
    response = client.get("/bookings/request")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_unauthenticated_user_cannot_submit_booking_request(
    app, client, available_equipment
):
    """Unauthenticated POST request to /bookings/request is rejected with redirect to login,

    and absolutely no booking is written to the database.
    """
    target_date = (date.today() + timedelta(days=2)).isoformat()

    response = client.post(
        "/bookings/request",
        data={
            "equipment_id": available_equipment,
            "booking_date": target_date,
            "start_time": "09:00",
            "end_time": "11:00",
        },
    )

    # Must redirect to login page
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]

    # Verify no booking record was created
    with app.app_context():
        assert Booking.query.count() == 0
