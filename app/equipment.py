from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required

from app import db
from app.auth import staff_required
from app.models import Equipment

equipment_bp = Blueprint("equipment", __name__, url_prefix="/equipment")


def read_equipment_form(form):
    """Read and validate the equipment form. Returns (values, error_message)."""
    values = {
        "name": form.get("name", "").strip(),
        "category": form.get("category", "").strip(),
        "description": form.get("description", "").strip(),
        "status": form.get("status", Equipment.STATUS_AVAILABLE),
    }

    if not values["name"]:
        return values, "Equipment name is required."
    if len(values["name"]) > 100:
        return values, "Equipment name must be at most 100 characters."
    if not values["category"]:
        return values, "Category is required."
    if len(values["category"]) > 50:
        return values, "Category must be at most 50 characters."
    if len(values["description"]) > 250:
        return values, "Description must be at most 250 characters."
    if values["status"] not in Equipment.VALID_STATUSES:
        return values, "Status must be Available or Out of service."

    return values, None


@equipment_bp.route("/")
@login_required
def list_equipment():
    """List equipment for all logged-in users, with optional category filter."""
    selected_category = request.args.get("category", "").strip()

    query = Equipment.query
    if selected_category:
        query = query.filter_by(category=selected_category)
    items = query.order_by(Equipment.name).all()

    categories = [
        row[0]
        for row in db.session.query(Equipment.category)
        .distinct()
        .order_by(Equipment.category)
        .all()
    ]

    return render_template(
        "equipment/list.html",
        items=items,
        categories=categories,
        selected_category=selected_category,
    )


@equipment_bp.route("/add", methods=["GET", "POST"])
@staff_required
def add_equipment():
    """Staff only: add a new equipment item."""
    if request.method == "POST":
        values, error = read_equipment_form(request.form)
        if error:
            flash(error, "error")
            return (
                render_template(
                    "equipment/form.html",
                    title="Add Equipment",
                    values=values,
                    statuses=Equipment.VALID_STATUSES,
                ),
                400,
            )

        db.session.add(Equipment(**values))
        db.session.commit()
        flash("Equipment added successfully.", "success")
        return redirect(url_for("equipment.list_equipment"))

    return render_template(
        "equipment/form.html",
        title="Add Equipment",
        values={"status": Equipment.STATUS_AVAILABLE},
        statuses=Equipment.VALID_STATUSES,
    )


@equipment_bp.route("/<int:equipment_id>/edit", methods=["GET", "POST"])
@staff_required
def edit_equipment(equipment_id):
    """Staff only: edit an equipment item."""
    item = db.get_or_404(Equipment, equipment_id)

    if request.method == "POST":
        values, error = read_equipment_form(request.form)
        if error:
            flash(error, "error")
            return (
                render_template(
                    "equipment/form.html",
                    title="Edit Equipment",
                    values=values,
                    statuses=Equipment.VALID_STATUSES,
                ),
                400,
            )

        item.name = values["name"]
        item.category = values["category"]
        item.description = values["description"]
        item.status = values["status"]
        db.session.commit()
        flash("Equipment updated successfully.", "success")
        return redirect(url_for("equipment.list_equipment"))

    return render_template(
        "equipment/form.html",
        title="Edit Equipment",
        values={
            "name": item.name,
            "category": item.category,
            "description": item.description or "",
            "status": item.status,
        },
        statuses=Equipment.VALID_STATUSES,
    )


@equipment_bp.route("/<int:equipment_id>/delete", methods=["POST"])
@staff_required
def delete_equipment(equipment_id):
    """Staff only: delete an equipment item."""
    item = db.get_or_404(Equipment, equipment_id)
    db.session.delete(item)
    db.session.commit()
    flash("Equipment deleted.", "info")
    return redirect(url_for("equipment.list_equipment"))