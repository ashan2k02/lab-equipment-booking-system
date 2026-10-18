import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app import db
from app.models import User

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


@auth_bp.route("/register", methods=["GET", "POST"])
@auth_bp.route("/auth/register", methods=["GET", "POST"])
def register():
    """Register a new student account.

    Public registration strictly creates Student accounts only. Any submitted
    role is explicitly ignored to prevent unauthorized privilege escalation.
    """
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
    """Placeholder login view so redirects and navbar links resolve."""
    return render_template("auth/login.html")


@auth_bp.route("/logout")
@auth_bp.route("/auth/logout")
def logout():
    """Placeholder logout view."""
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
