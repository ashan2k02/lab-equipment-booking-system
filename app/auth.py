import re
from functools import wraps
from urllib.parse import urlsplit

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app import db
from app.models import Booking, Equipment, User

auth_bp = Blueprint("auth", __name__)

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]+$")


def validate_registration_input(
    username: str | None,
    email: str | None,
    password: str | None,
    confirm_password: str | None,
) -> tuple[bool, str | None]:
    """Validate registration form fields and return (is_valid, error_message)."""
    if not username or not username.strip():
        return False, "Username is required."

    cleaned_username = username.strip()
    if len(cleaned_username) < 3:
        return False, "Username must be at least 3 characters long."

    if len(cleaned_username) > 80:
        return False, "Username must be at most 80 characters long."

    if not USERNAME_REGEX.match(cleaned_username):
        return False, "Username can only contain letters, numbers, and underscores."

    if not email or not email.strip():
        return False, "Email is required."

    cleaned_email = email.strip()
    if len(cleaned_email) > 120 or not EMAIL_REGEX.match(cleaned_email):
        return False, "Please provide a valid email address."

    if not password:
        return False, "Password is required."

    if len(password) < 6:
        return False, "Password must be at least 6 characters long."

    if password != confirm_password:
        return False, "Passwords do not match."

    return True, None


def role_required(*roles: str):
    """Decorator to restrict route access to authenticated users having one of the specified roles.

    Unauthenticated requests are redirected to login via Flask-Login.
    Authenticated users lacking one of the required roles are rejected with HTTP 403 Forbidden.
    """

    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator


roles_required = role_required


def staff_required(f):
    """Decorator to restrict access to authenticated Staff users only."""
    return role_required(User.ROLE_STAFF)(f)


def student_required(f):
    """Decorator to restrict access to authenticated Student users only."""
    return role_required(User.ROLE_STUDENT)(f)


def permission_required(permission_name: str):
    """Decorator to restrict route access based on a User capability/permission check.

    Evaluates the named method or attribute on current_user (e.g., 'can_manage_equipment',
    'can_review_bookings'). If False or missing, raises HTTP 403 Forbidden.
    """

    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            check = getattr(current_user, permission_name, None)
            allowed = check() if callable(check) else bool(check)
            if not allowed:
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator


@auth_bp.route("/register", methods=["GET", "POST"])
@auth_bp.route("/auth/register", methods=["GET", "POST"])
def register():
    """Register a new student account.

    Public registration strictly creates Student accounts only. Any submitted
    role is explicitly ignored to prevent unauthorized privilege escalation.
    """
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    if request.method == "POST":
        raw_username = request.form.get("username", "")
        raw_email = request.form.get("email", "")
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        is_valid, error_message = validate_registration_input(
            username=raw_username,
            email=raw_email,
            password=password,
            confirm_password=confirm_password,
        )

        username = raw_username.strip() if raw_username else ""
        email = raw_email.strip().lower() if raw_email else ""

        if not is_valid:
            flash(error_message, "error")
            return (
                render_template(
                    "auth/register.html",
                    username=username,
                    email=email,
                ),
                400,
            )

        # Check for duplicate username
        if User.query.filter_by(username=username).first() is not None:
            flash("Username is already taken. Please choose another.", "error")
            return (
                render_template(
                    "auth/register.html",
                    username=username,
                    email=email,
                ),
                400,
            )

        # Check for duplicate email
        if User.query.filter_by(email=email).first() is not None:
            flash(
                "Email is already registered. Please use another email or log in.",
                "error",
            )
            return (
                render_template(
                    "auth/register.html",
                    username=username,
                    email=email,
                ),
                400,
            )

        # Never trust a submitted role: public registration always creates a Student
        new_user = User(
            username=username,
            email=email,
            role=User.ROLE_STUDENT,
            password=password,
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for("auth.login"))
        except IntegrityError:
            db.session.rollback()
            flash("A user with this username or email already exists.", "error")
            return (
                render_template(
                    "auth/register.html",
                    username=username,
                    email=email,
                ),
                400,
            )
        except SQLAlchemyError:
            db.session.rollback()
            flash(
                "Registration failed due to a database error. Please try again.",
                "error",
            )
            return (
                render_template(
                    "auth/register.html",
                    username=username,
                    email=email,
                ),
                500,
            )

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
@auth_bp.route("/auth/login", methods=["GET", "POST"])
def login():
    """Authenticate and log in students and staff."""
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    if request.method == "POST":
        identifier = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        if not identifier:
            flash("Username or email is required.", "error")
            return render_template("auth/login.html", username=identifier), 400

        if not password:
            flash("Password is required.", "error")
            return render_template("auth/login.html", username=identifier), 400

        # Support login via username or email (case-insensitive email matching)
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()

        if user is None or not user.check_password(password):
            flash("Invalid username or password.", "error")
            return render_template("auth/login.html", username=identifier), 401

        login_user(user, remember=remember)
        flash(f"Welcome back, {user.username}!", "success")

        next_page = request.args.get("next")
        if not next_page or urlsplit(next_page).netloc != "":
            next_page = url_for("auth.dashboard")

        return redirect(next_page)

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@auth_bp.route("/auth/logout")
@login_required
def logout():
    """Terminate the authenticated session."""
    logout_user()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/dashboard")
@login_required
def dashboard():
    """Protected user dashboard displaying profile details and role."""
    return render_template("auth/dashboard.html", user=current_user)


@auth_bp.route("/staff/dashboard")
@staff_required
def staff_dashboard():
    """Protected staff-only view demonstrating role restriction and operations."""
    total_equipment = Equipment.query.count()
    available_equipment = Equipment.query.filter_by(
        status=Equipment.STATUS_AVAILABLE
    ).count()
    out_of_service_equipment = Equipment.query.filter_by(
        status=Equipment.STATUS_OUT_OF_SERVICE
    ).count()
    pending_bookings_count = Booking.query.filter_by(
        status=Booking.STATUS_PENDING
    ).count()
    recent_equipment = Equipment.query.order_by(Equipment.id.desc()).limit(5).all()

    return render_template(
        "auth/staff_dashboard.html",
        user=current_user,
        total_equipment=total_equipment,
        available_equipment=available_equipment,
        out_of_service_equipment=out_of_service_equipment,
        pending_bookings_count=pending_bookings_count,
        recent_equipment=recent_equipment,
    )
