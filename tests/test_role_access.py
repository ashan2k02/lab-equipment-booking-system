import pytest
from flask import abort

from app import create_app, db
from app.auth import (
    permission_required,
    role_required,
    roles_required,
    staff_required,
    student_required,
)
from app.models import User


@pytest.fixture
def app():
    test_app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        }
    )

    # Register demonstration endpoints to test decorators simulating M2/M3 functionality
    @test_app.route("/test/student-only")
    @student_required
    def test_student_only_route():
        return "Student Only Area", 200

    @test_app.route("/test/roles-allowed")
    @roles_required(User.ROLE_STUDENT, User.ROLE_STAFF)
    def test_both_roles_allowed():
        return "Both Roles Allowed Area", 200

    @test_app.route("/test/role-staff-only")
    @role_required(User.ROLE_STAFF)
    def test_role_staff_only():
        return "Staff Only Via Role Required", 200

    @test_app.route("/test/staff-required-route")
    @staff_required
    def test_staff_required_endpoint():
        return "Staff Required Area", 200

    @test_app.route("/test/equipment/manage", methods=["POST"])
    @permission_required("can_manage_equipment")
    def test_manage_equipment():
        return "Equipment Managed Successfully", 200

    @test_app.route("/test/bookings/review", methods=["POST"])
    @permission_required("can_review_bookings")
    def test_review_booking():
        return "Booking Review Successful", 200

    @test_app.route("/test/bookings/request", methods=["POST"])
    @permission_required("can_request_bookings")
    def test_request_booking():
        return "Booking Request Submitted", 200

    @test_app.route("/test/invalid-permission")
    @permission_required("undefined_permission_capability")
    def test_invalid_permission():
        return "Should Never Be Reached", 200

    @test_app.route("/test/trigger-401")
    def trigger_401():
        abort(401)

    @test_app.route("/test/trigger-403")
    def trigger_403():
        abort(403)

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
def student_user(app):
    with app.app_context():
        student = User(
            username="student_alex",
            email="alex@university.ac.lk",
            role=User.ROLE_STUDENT,
            password="studentpass123",
        )
        db.session.add(student)
        db.session.commit()
        return student.id


@pytest.fixture
def staff_user(app):
    with app.app_context():
        staff = User(
            username="staff_dr_smith",
            email="smith@university.ac.lk",
            role=User.ROLE_STAFF,
            password="staffpass123",
        )
        db.session.add(staff)
        db.session.commit()
        return staff.id


# ============================================================================
# User Model Role & Capability Tests
# ============================================================================


def test_user_roles_and_capabilities(app, student_user, staff_user):
    with app.app_context():
        student = db.session.get(User, student_user)
        staff = db.session.get(User, staff_user)

        # Student verification
        assert student.is_student is True
        assert student.is_staff is False
        assert student.has_role(User.ROLE_STUDENT) is True
        assert student.has_role(User.ROLE_STAFF) is False
        assert student.has_role("Admin", "Staff") is False

        # Staff verification
        assert staff.is_staff is True
        assert staff.is_student is False
        assert staff.has_role(User.ROLE_STAFF) is True
        assert staff.has_role(User.ROLE_STUDENT) is False

        # Domain permission capabilities
        # FR-01: Only staff can manage equipment
        assert student.can_manage_equipment() is False
        assert staff.can_manage_equipment() is True

        # FR-04: Only staff can approve or reject bookings
        assert student.can_review_bookings() is False
        assert staff.can_review_bookings() is True

        # FR-02: Authenticated users can submit booking requests
        assert student.can_request_bookings() is True
        assert staff.can_request_bookings() is True


def test_user_model_role_validation():
    with pytest.raises(ValueError, match="Invalid role"):
        User(username="bad_role", email="bad@uni.ac.lk", role="Administrator")


# ============================================================================
# Staff Route Restrictions & Custom 403 Forbidden Error Page
# ============================================================================


def test_staff_dashboard_unauthenticated_redirects(client):
    response = client.get("/staff/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_staff_dashboard_student_access_denied_with_custom_403(client, student_user):
    # Log in as student
    client.post(
        "/login",
        data={"username": "student_alex", "password": "studentpass123"},
    )

    response = client.get("/staff/dashboard")
    assert response.status_code == 403
    assert b"Access Denied (403 Forbidden)" in response.data
    assert b"Return to Dashboard" in response.data
    assert b"Log Out" in response.data


def test_staff_dashboard_staff_access_allowed(client, staff_user):
    # Log in as staff
    client.post(
        "/login",
        data={"username": "staff_dr_smith", "password": "staffpass123"},
    )

    response = client.get("/staff/dashboard")
    assert response.status_code == 200
    assert b"Staff Administration Console" in response.data
    assert b"Add, edit, and delete equipment (FR-01)" in response.data
    assert b"Review and approve or reject booking requests (FR-04)" in response.data


# ============================================================================
# Student Required Decorator Tests
# ============================================================================


def test_student_required_decorator(client, student_user, staff_user):
    # 1. Unauthenticated -> 302 Redirect to Login
    anon_res = client.get("/test/student-only", follow_redirects=False)
    assert anon_res.status_code == 302
    assert "/login" in anon_res.headers["Location"]

    # 2. Staff user -> 403 Forbidden
    client.post(
        "/login",
        data={"username": "staff_dr_smith", "password": "staffpass123"},
    )
    staff_res = client.get("/test/student-only")
    assert staff_res.status_code == 403
    client.get("/logout")

    # 3. Student user -> 200 OK
    client.post(
        "/login",
        data={"username": "student_alex", "password": "studentpass123"},
    )
    student_res = client.get("/test/student-only")
    assert student_res.status_code == 200
    assert b"Student Only Area" in student_res.data


# ============================================================================
# Role Required / Roles Required Decorator Tests
# ============================================================================


def test_role_required_staff_only(client, student_user, staff_user):
    # Unauthenticated
    assert client.get("/test/role-staff-only").status_code == 302

    # Student denied
    client.post(
        "/login",
        data={"username": "student_alex", "password": "studentpass123"},
    )
    assert client.get("/test/role-staff-only").status_code == 403
    client.get("/logout")

    # Staff allowed
    client.post(
        "/login",
        data={"username": "staff_dr_smith", "password": "staffpass123"},
    )
    assert client.get("/test/role-staff-only").status_code == 200


def test_roles_required_multiple_roles(client, student_user, staff_user):
    # Unauthenticated
    assert client.get("/test/roles-allowed").status_code == 302

    # Student allowed
    client.post(
        "/login",
        data={"username": "student_alex", "password": "studentpass123"},
    )
    res_student = client.get("/test/roles-allowed")
    assert res_student.status_code == 200
    assert b"Both Roles Allowed Area" in res_student.data
    client.get("/logout")

    # Staff allowed
    client.post(
        "/login",
        data={"username": "staff_dr_smith", "password": "staffpass123"},
    )
    res_staff = client.get("/test/roles-allowed")
    assert res_staff.status_code == 200
    assert b"Both Roles Allowed Area" in res_staff.data


# ============================================================================
# Permission Required Decorator Tests (Equipment & Booking Capabilities)
# ============================================================================


def test_equipment_management_permission_enforcement(client, student_user, staff_user):
    """Verify that students are strictly prevented from managing equipment."""
    # 1. Unauthenticated -> 302
    assert client.post("/test/equipment/manage").status_code == 302

    # 2. Student attempt -> 403 Forbidden
    client.post(
        "/login",
        data={"username": "student_alex", "password": "studentpass123"},
    )
    res_student = client.post("/test/equipment/manage")
    assert res_student.status_code == 403
    assert b"Access Denied (403 Forbidden)" in res_student.data
    client.get("/logout")

    # 3. Staff attempt -> 200 OK
    client.post(
        "/login",
        data={"username": "staff_dr_smith", "password": "staffpass123"},
    )
    res_staff = client.post("/test/equipment/manage")
    assert res_staff.status_code == 200
    assert b"Equipment Managed Successfully" in res_staff.data


def test_booking_review_permission_enforcement(client, student_user, staff_user):
    """Verify that students are strictly prevented from approving/rejecting bookings."""
    # 1. Student attempt -> 403 Forbidden
    client.post(
        "/login",
        data={"username": "student_alex", "password": "studentpass123"},
    )
    res_student = client.post("/test/bookings/review")
    assert res_student.status_code == 403
    client.get("/logout")

    # 2. Staff attempt -> 200 OK
    client.post(
        "/login",
        data={"username": "staff_dr_smith", "password": "staffpass123"},
    )
    res_staff = client.post("/test/bookings/review")
    assert res_staff.status_code == 200
    assert b"Booking Review Successful" in res_staff.data


def test_booking_request_permission(client, student_user):
    client.post(
        "/login",
        data={"username": "student_alex", "password": "studentpass123"},
    )
    res = client.post("/test/bookings/request")
    assert res.status_code == 200
    assert b"Booking Request Submitted" in res.data


def test_invalid_or_missing_permission_attribute(client, staff_user):
    """Undefined permission method must safely fail-closed and return 403."""
    client.post(
        "/login",
        data={"username": "staff_dr_smith", "password": "staffpass123"},
    )
    res = client.get("/test/invalid-permission")
    assert res.status_code == 403


def test_staff_required_decorator(client, student_user, staff_user):
    # 1. Unauthenticated -> 302
    assert client.get("/test/staff-required-route").status_code == 302

    # 2. Student denied -> 403
    client.post(
        "/login",
        data={"username": "student_alex", "password": "studentpass123"},
    )
    assert client.get("/test/staff-required-route").status_code == 403
    client.get("/logout")

    # 3. Staff allowed -> 200
    client.post(
        "/login",
        data={"username": "staff_dr_smith", "password": "staffpass123"},
    )
    res_staff = client.get("/test/staff-required-route")
    assert res_staff.status_code == 200
    assert b"Staff Required Area" in res_staff.data


# ============================================================================
# Custom 401 & 403 Error Templates Tests
# ============================================================================


def test_custom_401_error_page(client):
    response = client.get("/test/trigger-401")
    assert response.status_code == 401
    assert b"Authentication Required (401)" in response.data
    assert b"Log In" in response.data


def test_custom_403_error_page_unauthenticated(client):
    """403 response when rendered for unauthenticated visitor."""
    response = client.get("/test/trigger-403")
    assert response.status_code == 403
    assert b"Access Denied (403 Forbidden)" in response.data
    assert b"Log In" in response.data
