from datetime import date, datetime, time
from typing import Any

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.auth import staff_required
from app.models import Booking, Equipment

bookings_bp = Blueprint("bookings", __name__, url_prefix="/bookings")


def validate_booking_input(
    equipment_id_raw: Any,
    booking_date_raw: str | None,
    start_time_raw: str | None,
    end_time_raw: str | None,
) -> tuple[bool, str | None, dict[str, Any] | None]:
    """Validate user input for booking equipment and return (is_valid, error_message, parsed_data)."""
    current_datetime = datetime.now()
    current_date = current_datetime.date()

    # 1. Validate equipment selection
    if not equipment_id_raw:
        return False, "Please select an equipment item.", None

    try:
        equipment_id = int(equipment_id_raw)
    except (ValueError, TypeError):
        return False, "Invalid equipment selected.", None

    equipment = db.session.get(Equipment, equipment_id)
    if not equipment:
        return False, "The selected equipment does not exist.", None

    if equipment.status not in Equipment.VALID_STATUSES:
        return (
            False,
            f"'{equipment.name}' has an invalid availability status and cannot be booked.",
            None,
        )

    if equipment.status == Equipment.STATUS_OUT_OF_SERVICE:
        return (
            False,
            f"'{equipment.name}' is currently out of service and cannot be booked.",
            None,
        )

    if equipment.status != Equipment.STATUS_AVAILABLE:
        return False, f"'{equipment.name}' is currently unavailable and cannot be booked.", None

    # 2. Validate booking date
    if not booking_date_raw or not booking_date_raw.strip():
        return False, "Booking date is required.", None

    try:
        booking_date = date.fromisoformat(booking_date_raw.strip())
    except (TypeError, ValueError):
        return False, "Invalid booking date format. Please use YYYY-MM-DD.", None

    if booking_date < current_date:
        return False, "Booking date cannot be in the past.", None

    # 3. Validate start and end time
    if not start_time_raw or not start_time_raw.strip():
        return False, "Start time is required.", None

    if not end_time_raw or not end_time_raw.strip():
        return False, "End time is required.", None

    try:
        start_cleaned = start_time_raw.strip()
        if len(start_cleaned.split(":")) == 2:
            start_cleaned = f"{start_cleaned}:00"
        start_time = time.fromisoformat(start_cleaned)
    except (TypeError, ValueError):
        return False, "Invalid start time format. Please use HH:MM.", None

    try:
        end_cleaned = end_time_raw.strip()
        if len(end_cleaned.split(":")) == 2:
            end_cleaned = f"{end_cleaned}:00"
        end_time = time.fromisoformat(end_cleaned)
    except (TypeError, ValueError):
        return False, "Invalid end time format. Please use HH:MM.", None

    if end_time <= start_time:
        return False, "End time must be later than start time.", None

    duration_seconds = (
        datetime.combine(booking_date, end_time)
        - datetime.combine(booking_date, start_time)
    ).total_seconds()
    if duration_seconds < 30 * 60:
        return False, "Booking duration must be at least 30 minutes.", None

    if duration_seconds > 4 * 60 * 60:
        return False, "Booking duration cannot exceed 4 hours.", None

    # If booking is for today, verify start time has not already passed
    if booking_date == current_date and start_time < current_datetime.time():
        return False, "Booking cannot start in the past.", None

    conflicting_booking = Booking.query.filter(
        Booking.equipment_id == equipment.id,
        Booking.booking_date == booking_date,
        Booking.status.in_((Booking.STATUS_PENDING, Booking.STATUS_APPROVED)),
        Booking.start_time < end_time,
        Booking.end_time > start_time,
    ).first()
    if conflicting_booking:
        return (
            False,
            "This equipment already has a Pending or Approved booking that overlaps the requested time.",
            None,
        )

    return (
        True,
        None,
        {
            "equipment": equipment,
            "booking_date": booking_date,
            "start_time": start_time,
            "end_time": end_time,
        },
    )


@bookings_bp.route("/request", methods=["GET", "POST"])
@bookings_bp.route("/new", methods=["GET", "POST"])
@login_required
def request_booking():
    """FR-02: Allows students to select equipment, date, start and end time,

    and submit a booking request. Initial status is always 'Pending'.
    """
    # Fetch equipment catalogue items (available items prioritized)
    available_equipment = Equipment.query.order_by(
        Equipment.category, Equipment.name
    ).all()

    today_str = date.today().isoformat()
    selected_equipment_id = request.args.get("equipment_id", type=int)

    if request.method == "POST":
        raw_equipment_id = request.form.get("equipment_id")
        raw_booking_date = request.form.get("booking_date")
        raw_start_time = request.form.get("start_time")
        raw_end_time = request.form.get("end_time")

        is_valid, error_msg, parsed_data = validate_booking_input(
            equipment_id_raw=raw_equipment_id,
            booking_date_raw=raw_booking_date,
            start_time_raw=raw_start_time,
            end_time_raw=raw_end_time,
        )

        if not is_valid:
            flash(error_msg, "error")
            return (
                render_template(
                    "bookings/request.html",
                    equipment_list=available_equipment,
                    selected_equipment_id=raw_equipment_id,
                    booking_date=raw_booking_date,
                    start_time=raw_start_time,
                    end_time=raw_end_time,
                    min_date=today_str,
                ),
                400,
            )

        # FR-02 Security & Business Rule:
        # Every valid new booking request must be saved with its initial status set to 'Pending'.
        # Any form field attempting to specify or override 'status' (e.g., 'Approved') is strictly ignored.
        new_booking = Booking(
            user_id=current_user.id,
            equipment_id=parsed_data["equipment"].id,
            booking_date=parsed_data["booking_date"],
            start_time=parsed_data["start_time"],
            end_time=parsed_data["end_time"],
            status=Booking.STATUS_PENDING,
        )

        db.session.add(new_booking)
        db.session.commit()

        flash(
            f"Booking request for '{parsed_data['equipment'].name}' submitted successfully! "
            f"Your request is now Pending review.",
            "success",
        )
        return redirect(url_for("bookings.my_bookings"))

    return render_template(
        "bookings/request.html",
        equipment_list=available_equipment,
        selected_equipment_id=selected_equipment_id,
        min_date=today_str,
    )


@bookings_bp.route("/my-bookings")
@login_required
def my_bookings():
    """Display the list of bookings requested by the current logged-in user."""
    user_bookings = (
        Booking.query.filter_by(user_id=current_user.id)
        .order_by(Booking.booking_date.desc(), Booking.start_time.desc())
        .all()
    )
    return render_template("bookings/my_bookings.html", bookings=user_bookings)


@bookings_bp.route("/pending")
@staff_required
def pending_bookings():
    """Display pending booking requests for authorized staff members."""
    pending_requests = (
        Booking.query.filter_by(status=Booking.STATUS_PENDING)
        .order_by(Booking.booking_date, Booking.start_time, Booking.created_at)
        .all()
    )
    return render_template(
        "bookings/pending_bookings.html", bookings=pending_requests
    )


@bookings_bp.route("/<int:booking_id>")
@login_required
def booking_detail(booking_id: int):
    """View details of an individual booking."""
    booking = db.session.get(Booking, booking_id)
    if not booking:
        abort(404)

    # Students can only view their own bookings; Staff can view any booking
    if not current_user.is_staff and booking.user_id != current_user.id:
        abort(403)

    return render_template("bookings/detail.html", booking=booking)


@bookings_bp.route("/<int:booking_id>/accept", methods=["POST"])
@bookings_bp.route("/<int:booking_id>/approve", methods=["POST"])
@staff_required
def accept_booking(booking_id: int):
    """Staff only: accept/approve a pending booking request."""
    booking = db.session.get(Booking, booking_id)
    if not booking:
        abort(404)

    if booking.status != Booking.STATUS_PENDING:
        flash(
            f"Booking #{booking.id} cannot be accepted because it is already {booking.status}.",
            "error",
        )
        return redirect(url_for("bookings.pending_bookings"))

    # Check if equipment is out of service
    if booking.equipment and booking.equipment.status == Equipment.STATUS_OUT_OF_SERVICE:
        flash(
            f"Cannot accept Booking #{booking.id}: '{booking.equipment.name}' is currently marked Out of service.",
            "error",
        )
        return redirect(url_for("bookings.pending_bookings"))

    # Check for overlapping Approved bookings for the same equipment
    conflicting = Booking.query.filter(
        Booking.id != booking.id,
        Booking.equipment_id == booking.equipment_id,
        Booking.booking_date == booking.booking_date,
        Booking.status == Booking.STATUS_APPROVED,
        Booking.start_time < booking.end_time,
        Booking.end_time > booking.start_time,
    ).first()

    if conflicting:
        flash(
            f"Cannot accept Booking #{booking.id}: this equipment already has an approved booking during that time window.",
            "error",
        )
        return redirect(url_for("bookings.pending_bookings"))

    try:
        booking.status = Booking.STATUS_APPROVED
        db.session.commit()
        equip_name = booking.equipment.name if booking.equipment else "equipment"
        flash(
            f"Booking #{booking.id} for '{equip_name}' accepted successfully.",
            "success",
        )
    except SQLAlchemyError:
        db.session.rollback()
        flash("Failed to accept booking due to a database error.", "error")

    next_page = request.form.get("next") or request.args.get("next")
    if next_page and next_page.startswith("/") and not next_page.startswith("//"):
        return redirect(next_page)
    return redirect(url_for("bookings.pending_bookings"))


@bookings_bp.route("/<int:booking_id>/reject", methods=["POST"])
@bookings_bp.route("/<int:booking_id>/decline", methods=["POST"])
@staff_required
def reject_booking(booking_id: int):
    """Staff only: decline/reject a pending booking request with an optional reason."""
    booking = db.session.get(Booking, booking_id)
    if not booking:
        abort(404)

    if booking.status != Booking.STATUS_PENDING:
        flash(
            f"Booking #{booking.id} cannot be declined because it is already {booking.status}.",
            "error",
        )
        return redirect(url_for("bookings.pending_bookings"))

    reason = request.form.get("rejection_reason", "").strip()

    try:
        booking.status = Booking.STATUS_REJECTED
        booking.rejection_reason = reason if reason else None
        db.session.commit()
        equip_name = booking.equipment.name if booking.equipment else "equipment"
        flash(
            f"Booking #{booking.id} for '{equip_name}' has been declined.",
            "info",
        )
    except SQLAlchemyError:
        db.session.rollback()
        flash("Failed to decline booking due to a database error.", "error")

    next_page = request.form.get("next") or request.args.get("next")
    if next_page and next_page.startswith("/") and not next_page.startswith("//"):
        return redirect(next_page)
    return redirect(url_for("bookings.pending_bookings"))
