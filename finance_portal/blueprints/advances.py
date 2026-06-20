from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, abort,
)
from flask_login import login_required, current_user
from datetime import datetime

from ..extensions import db
from ..models import Event, Advance
from ..forms import AdvanceForm, RejectForm, SettlementForm
from ..decorators import committee_required
from ..services import record_audit, audit_for
from ..workflow import inbox_for
from . import _helpers as H
from .. import constants as C

advances_bp = Blueprint("advances", __name__, url_prefix="/advances")
DETAIL = "advances.detail"
LIST = "advances.index"


@advances_bp.route("/")
@login_required
def index():
    advances = Advance.query.order_by(Advance.updated_at.desc()).all()
    return render_template("advances/list.html", advances=advances,
                           inbox_statuses=inbox_for(current_user))


@advances_bp.route("/<int:item_id>")
@login_required
def detail(item_id):
    advance = db.get_or_404(Advance, item_id)
    return render_template(
        "advances/detail.html", advance=advance,
        history=audit_for(C.TYPE_ADVANCE, advance.id),
        can_edit=H.can_edit(advance),
        can_act=current_user.is_approver and advance.status in inbox_for(current_user),
        reject_form=RejectForm(), settle_form=SettlementForm(),
    )


@advances_bp.route("/new", methods=["GET", "POST"])
@advances_bp.route("/new/<int:event_id>", methods=["GET", "POST"])
@committee_required
def create(event_id=None):
    form = AdvanceForm()
    events = Event.query.order_by(Event.name).all()
    if form.validate_on_submit():
        ev_id = request.form.get("event_id", type=int) or event_id
        if not ev_id:
            flash("Please choose an event.", "danger")
            return render_template("advances/form.html", form=form, events=events,
                                   mode="create", event_id=event_id, advance=None)
        advance = Advance(event_id=ev_id, purpose=form.purpose.data,
                          requested_for=form.requested_for.data,
                          amount=form.amount.data, created_by_id=current_user.id,
                          status=C.STATUS_DRAFT)
        db.session.add(advance)
        db.session.flush()
        record_audit(C.TYPE_ADVANCE, advance.id, C.ACTION_CREATE, current_user,
                     f"Created advance request '{advance.purpose}' ({advance.amount}).")
        db.session.commit()
        flash("Advance request saved as draft.", "success")
        return redirect(url_for(DETAIL, item_id=advance.id))
    return render_template("advances/form.html", form=form, events=events,
                           mode="create", event_id=event_id, advance=None)


@advances_bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
@committee_required
def edit(item_id):
    advance = db.get_or_404(Advance, item_id)
    if not H.can_edit(advance):
        abort(403)
    form = AdvanceForm(obj=advance)
    events = Event.query.order_by(Event.name).all()
    if form.validate_on_submit():
        advance.purpose = form.purpose.data
        advance.requested_for = form.requested_for.data
        advance.amount = form.amount.data
        record_audit(C.TYPE_ADVANCE, advance.id, C.ACTION_EDIT, current_user,
                     f"Edited advance '{advance.purpose}'.")
        db.session.commit()
        flash("Advance updated.", "success")
        return redirect(url_for(DETAIL, item_id=advance.id))
    return render_template("advances/form.html", form=form, events=events,
                           mode="edit", advance=advance, event_id=advance.event_id)


@advances_bp.route("/<int:item_id>/submit", methods=["POST"])
@committee_required
def submit(item_id):
    return H.do_submit(db.get_or_404(Advance, item_id), DETAIL)


@advances_bp.route("/<int:item_id>/approve", methods=["POST"])
@login_required
def approve(item_id):
    return H.do_approve(db.get_or_404(Advance, item_id), DETAIL)


@advances_bp.route("/<int:item_id>/reject", methods=["POST"])
@login_required
def reject(item_id):
    form = RejectForm()
    reason = form.reason.data if form.validate_on_submit() else "No reason provided"
    return H.do_reject(db.get_or_404(Advance, item_id), reason, DETAIL)


@advances_bp.route("/<int:item_id>/settle", methods=["POST"])
@committee_required
def settle(item_id):
    """Record settlement after the advance is approved."""
    advance = db.get_or_404(Advance, item_id)
    if advance.status != C.STATUS_APPROVED:
        flash("Only approved advances can be settled.", "danger")
        return redirect(url_for(DETAIL, item_id=advance.id))
    form = SettlementForm()
    if form.validate_on_submit():
        advance.settled_amount = form.settled_amount.data
        advance.settlement_notes = form.settlement_notes.data
        advance.settled_at = datetime.utcnow()
        advance.status = C.STATUS_SETTLED
        record_audit(C.TYPE_ADVANCE, advance.id, C.ACTION_SETTLE, current_user,
                     f"Settled advance with ₹{advance.settled_amount}.")
        db.session.commit()
        flash("Settlement recorded.", "success")
    return redirect(url_for(DETAIL, item_id=advance.id))


@advances_bp.route("/<int:item_id>/delete", methods=["POST"])
@committee_required
def delete(item_id):
    return H.do_delete(db.get_or_404(Advance, item_id), LIST)
