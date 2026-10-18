from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


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

    def set_password(self, password: str) -> None:
        if not password or not isinstance(password, str):
            raise ValueError("Password must be a non-empty string.")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not password or not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_staff(self) -> bool:
        return self.role == self.ROLE_STAFF

    @property
    def is_student(self) -> bool:
        return self.role == self.ROLE_STUDENT

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"


class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(250))
    status = db.Column(db.String(30), default="Available")