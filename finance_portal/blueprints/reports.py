from decimal import Decimal

from flask import Blueprint, render_template, send_file, request
from flask_login import login_required, current_user

from ..extensions import db
from ..models import (
    Event, Budget, Advance, VendorPayment, Reimbursement, PrizePool, User,
)
from ..pdf import income_expenditure_pdf
from .. import constants as C

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/")
@login_required
def index():
    events = Event.query.order_by(Event.created_at.desc()).all()
    grand_sanctioned = sum((e.approved_budget for e in events), Decimal("0.00"))
    grand_spent = sum((e.total_expenditure for e in events), Decimal("0.00"))
    return render_template("reports/index.html", events=events,
                           grand_sanctioned=grand_sanctioned,
                           grand_spent=grand_spent)


@reports_bp.route("/event/<int:event_id>")
@login_required
def event_report(event_id):
    event = db.get_or_404(Event, event_id)
    return render_template("reports/event.html", event=event)


@reports_bp.route("/event/<int:event_id>/pdf")
@login_required
def event_pdf(event_id):
    event = db.get_or_404(Event, event_id)
    buf = income_expenditure_pdf(event)
    return send_file(buf, mimetype="application/pdf", as_attachment=False,
                     download_name=f"income_expenditure_{event.id}.pdf")


@reports_bp.route("/committee")
@login_required
def committee_report():
    """Committee-wise roll-up of sanctioned vs spent across events."""
    events = Event.query.all()
    by_committee = {}
    for e in events:
        key = e.committee_name or "Unassigned"
        agg = by_committee.setdefault(
            key, {"events": 0, "sanctioned": Decimal("0.00"),
                  "spent": Decimal("0.00")})
        agg["events"] += 1
        agg["sanctioned"] += e.approved_budget
        agg["spent"] += e.total_expenditure
    for agg in by_committee.values():
        agg["balance"] = agg["sanctioned"] - agg["spent"]
    return render_template("reports/committee.html", by_committee=by_committee)
