from datetime import UTC, date, datetime, time

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


def hash_password(password: str) -> str:
    """Generate a secure cryptographic hash of a plaintext password."""
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string.")
    return generate_password_hash(password)


def verify_password(password_hash: str | None, password: str | None) -> bool:
    """Verify a plaintext password against a stored hash."""
    if not password or not password_hash:
        return False
    return check_password_hash(password_hash, password)


class User(UserMixin, db.Model):
    __tablename__ = "user"

    ROLE_STUDENT = "Student"
    ROLE_STAFF = "Staff"
    VALID_ROLES = (ROLE_STUDENT, ROLE_STAFF)

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_STUDENT)

    def __init__(
        self,
        username: str | None = None,
        email: str | None = None,
        role: str = ROLE_STUDENT,
        password: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if username is not None:
            self.username = username.strip()
        if email is not None:
            self.email = email.strip().lower()
        if role is not None:
            if role not in self.VALID_ROLES:
                raise ValueError(
                    f"Invalid role: {role!r}. Must be one of {self.VALID_ROLES}."
                )
            self.role = role
        if password is not None:
            self.set_password(password)

    @property
    def password(self):
        """Prevent reading of plaintext passwords."""
        raise AttributeError(
            "password is not a readable attribute; only password_hash is stored."
        )

    @password.setter
    def password(self, password: str) -> None:
        """Allow setting password directly via property assignment."""
        self.set_password(password)

    def set_password(self, password: str) -> None:
        self.password_hash = hash_password(password)

    def check_password(self, password: str) -> bool:
        return verify_password(self.password_hash, password)

    @property
    def is_staff(self) -> bool:
        return self.role == self.ROLE_STAFF

    @property
    def is_student(self) -> bool:
        return self.role == self.ROLE_STUDENT

    def has_role(self, *roles: str) -> bool:
        """Check whether the user possesses any of the specified roles."""
        return self.role in roles

    def can_manage_equipment(self) -> bool:
        """Determine whether the user can add, edit, or delete equipment (Staff only, FR-01)."""
        return self.is_staff

    def can_review_bookings(self) -> bool:
        """Determine whether the user can approve or reject booking requests (Staff only, FR-04)."""
        return self.is_staff

    def can_request_bookings(self) -> bool:
        """Determine whether the user can submit equipment booking requests (FR-02)."""
        return bool(self.is_authenticated)

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"


class Equipment(db.Model):
    __tablename__ = "equipment"

    STATUS_AVAILABLE = "Available"
    STATUS_OUT_OF_SERVICE = "Out of service"
    VALID_STATUSES = (STATUS_AVAILABLE, STATUS_OUT_OF_SERVICE)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(250))
    status = db.Column(db.String(30), default=STATUS_AVAILABLE)

    def __repr__(self) -> str:
        return f"<Equipment {self.name} ({self.status})>"


class Booking(db.Model):
    __tablename__ = "booking"

    STATUS_PENDING = "Pending"
    STATUS_APPROVED = "Approved"
    STATUS_REJECTED = "Rejected"
    STATUS_CANCELLED = "Cancelled"
    VALID_STATUSES = (
        STATUS_PENDING,
        STATUS_APPROVED,
        STATUS_REJECTED,
        STATUS_CANCELLED,
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    equipment_id = db.Column(db.Integer, db.ForeignKey("equipment.id"), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING)
    rejection_reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    user = db.relationship("User", backref=db.backref("bookings", lazy=True))
    equipment = db.relationship("Equipment", backref=db.backref("bookings", lazy=True))

    def __init__(
        self,
        user_id: int | None = None,
        equipment_id: int | None = None,
        booking_date: date | str | None = None,
        start_time: time | str | None = None,
        end_time: time | str | None = None,
        status: str = STATUS_PENDING,
        rejection_reason: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if user_id is not None:
            self.user_id = user_id
        if equipment_id is not None:
            self.equipment_id = equipment_id

        if booking_date is not None:
            if isinstance(booking_date, str):
                self.booking_date = date.fromisoformat(booking_date.strip())
            else:
                self.booking_date = booking_date

        if start_time is not None:
            if isinstance(start_time, str):
                cleaned = start_time.strip()
                if len(cleaned.split(":")) == 2:
                    cleaned = f"{cleaned}:00"
                self.start_time = time.fromisoformat(cleaned)
            else:
                self.start_time = start_time

        if end_time is not None:
            if isinstance(end_time, str):
                cleaned = end_time.strip()
                if len(cleaned.split(":")) == 2:
                    cleaned = f"{cleaned}:00"
                self.end_time = time.fromisoformat(cleaned)
            else:
                self.end_time = end_time

        if status is not None:
            if status not in self.VALID_STATUSES:
                raise ValueError(
                    f"Invalid booking status: {status!r}. Must be one of {self.VALID_STATUSES}."
                )
            self.status = status

        if rejection_reason is not None:
            self.rejection_reason = rejection_reason

    @property
    def is_pending(self) -> bool:
        return self.status == self.STATUS_PENDING

    @property
    def is_approved(self) -> bool:
        return self.status == self.STATUS_APPROVED

    @property
    def is_rejected(self) -> bool:
        return self.status == self.STATUS_REJECTED

    @property
    def is_cancelled(self) -> bool:
        return self.status == self.STATUS_CANCELLED

    @property
    def duration_minutes(self) -> int:
        if self.start_time and self.end_time:
            start_m = self.start_time.hour * 60 + self.start_time.minute
            end_m = self.end_time.hour * 60 + self.end_time.minute
            return end_m - start_m
        return 0

    def __repr__(self) -> str:
        return (
            f"<Booking id={self.id} user_id={self.user_id} "
            f"equipment_id={self.equipment_id} status={self.status}>"
        )
