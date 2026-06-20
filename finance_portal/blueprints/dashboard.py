"""Role-aware dashboard: KPIs, approval inbox, charts, recent activity."""
from decimal import Decimal

from flask import Blueprint, render_template
from flask_login import login_required, current_user

from ..extensions import db
from ..models import (
    Event, Budget, Advance, VendorPayment, Reimbursement, PrizePool, AuditLog,
)
from ..workflow import inbox_for
from .. import constants as C

dashboard_bp = Blueprint("dashboard", __name__)

REQUEST_MODELS = [Budget, Advance, VendorPayment, Reimbursement, PrizePool]


def _pending_for_role():
    """All requests across types currently awaiting the current user's role."""
    statuses = inbox_for(current_user)
    if not statuses:
        return []
    items = []
    for Model in REQUEST_MODELS:
        items += Model.query.filter(Model.status.in_(statuses)).all()
    items.sort(key=lambda x: x.updated_at or x.created_at, reverse=True)
    return items


@dashboard_bp.route("/")
@login_required
def index():
    events = Event.query.order_by(Event.created_at.desc()).all()

    total_sanctioned = sum((e.approved_budget for e in events), Decimal("0.00"))
    total_spent = sum((e.total_expenditure for e in events), Decimal("0.00"))
    balance = total_sanctioned - total_spent

    # Count pending across all types
    pending_total = 0
    for Model in REQUEST_MODELS:
        pending_total += Model.query.filter(
            Model.status.in_(C.PENDING_STATUSES)
        ).count()

    # Approval inbox for approver roles
    inbox = _pending_for_role() if current_user.is_approver else []

    # Per-event chart data (top 6 by sanctioned budget)
    chart_events = sorted(events, key=lambda e: e.approved_budget, reverse=True)[:6]
    chart = {
        "labels": [e.name for e in chart_events],
        "sanctioned": [float(e.approved_budget) for e in chart_events],
        "spent": [float(e.total_expenditure) for e in chart_events],
    }

    # Status distribution donut
    status_counts = {}
    for Model in REQUEST_MODELS:
        for st in C.STATUS_LABELS:
            cnt = Model.query.filter_by(status=st).count()
            if cnt:
                status_counts[st] = status_counts.get(st, 0) + cnt

    recent = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()

    return render_template(
        "dashboard.html",
        events=events,
        kpi={
            "events": len(events),
            "sanctioned": total_sanctioned,
            "spent": total_spent,
            "balance": balance,
            "pending": pending_total,
        },
        inbox=inbox,
        chart=chart,
        status_counts=status_counts,
        recent=recent,
    )
