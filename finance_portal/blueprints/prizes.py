from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, abort, send_file,
)
from flask_login import login_required, current_user
from datetime import datetime

from ..extensions import db
from ..models import Event, PrizePool, PrizeWinner
from ..forms import PrizePoolForm, RejectForm
from ..decorators import committee_required
from ..services import record_audit, audit_for
from ..workflow import inbox_for
from ..pdf import prize_pool_pdf
from . import _helpers as H
from .. import constants as C

prizes_bp = Blueprint("prizes", __name__, url_prefix="/prize-pools")
DETAIL = "prizes.detail"
LIST = "prizes.index"


def _parse_winners(pp):
    names = request.form.getlist("winner_name[]")
    amounts = request.form.getlist("winner_amount[]")
    accounts = request.form.getlist("winner_account[]")
    ifscs = request.form.getlist("winner_ifsc[]")
    for w in list(pp.winners):
        db.session.delete(w)
    pos = 1
    for name, amt, acc, ifsc in zip(names, amounts, accounts, ifscs):
        if not name.strip():
            continue
        pp.winners.append(PrizeWinner(
            position=pos, winner_name=name.strip(),
            prize_amount=H.to_decimal(amt, "0"),
            account_no=acc.strip(), ifsc=ifsc.strip()))
        pos += 1


@prizes_bp.route("/")
@login_required
def index():
    pools = PrizePool.query.order_by(PrizePool.updated_at.desc()).all()
    return render_template("prizes/list.html", pools=pools,
                           inbox_statuses=inbox_for(current_user))


@prizes_bp.route("/<int:item_id>")
@login_required
def detail(item_id):
    pp = db.get_or_404(PrizePool, item_id)
    return render_template(
        "prizes/detail.html", pp=pp,
        history=audit_for(C.TYPE_PRIZE, pp.id),
        can_edit=H.can_edit(pp),
        can_act=current_user.is_approver and pp.status in inbox_for(current_user),
        reject_form=RejectForm(),
    )


@prizes_bp.route("/new", methods=["GET", "POST"])
@prizes_bp.route("/new/<int:event_id>", methods=["GET", "POST"])
@committee_required
def create(event_id=None):
    form = PrizePoolForm()
    events = Event.query.order_by(Event.name).all()
    if request.method == "POST" and form.validate():
        ev_id = request.form.get("event_id", type=int) or event_id
        if not ev_id:
            flash("Please choose an event.", "danger")
            return render_template("prizes/form.html", form=form, events=events,
                                   mode="create", event_id=event_id, pp=None)
        pp = PrizePool(event_id=ev_id, competition_name=form.competition_name.data,
                       created_by_id=current_user.id, status=C.STATUS_DRAFT)
        db.session.add(pp)
        _parse_winners(pp)
        db.session.flush()
        record_audit(C.TYPE_PRIZE, pp.id, C.ACTION_CREATE, current_user,
                     f"Created prize pool '{pp.competition_name}' ({pp.total}).")
        db.session.commit()
        flash("Prize pool saved as draft.", "success")
        return redirect(url_for(DETAIL, item_id=pp.id))
    return render_template("prizes/form.html", form=form, events=events,
                           mode="create", event_id=event_id, pp=None)


@prizes_bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
@committee_required
def edit(item_id):
    pp = db.get_or_404(PrizePool, item_id)
    if not H.can_edit(pp):
        abort(403)
    form = PrizePoolForm(obj=pp)
    events = Event.query.order_by(Event.name).all()
    if request.method == "POST" and form.validate():
        pp.competition_name = form.competition_name.data
        _parse_winners(pp)
        record_audit(C.TYPE_PRIZE, pp.id, C.ACTION_EDIT, current_user,
                     f"Edited prize pool '{pp.competition_name}'.")
        db.session.commit()
        flash("Prize pool updated.", "success")
        return redirect(url_for(DETAIL, item_id=pp.id))
    return render_template("prizes/form.html", form=form, events=events,
                           mode="edit", pp=pp, event_id=pp.event_id)


@prizes_bp.route("/<int:item_id>/submit", methods=["POST"])
@committee_required
def submit(item_id):
    pp = db.get_or_404(PrizePool, item_id)
    if not pp.winners:
        flash("Add at least one winner before submitting.", "danger")
        return redirect(url_for(DETAIL, item_id=pp.id))
    return H.do_submit(pp, DETAIL)


@prizes_bp.route("/<int:item_id>/approve", methods=["POST"])
@login_required
def approve(item_id):
    return H.do_approve(db.get_or_404(PrizePool, item_id), DETAIL)


@prizes_bp.route("/<int:item_id>/reject", methods=["POST"])
@login_required
def reject(item_id):
    form = RejectForm()
    reason = form.reason.data if form.validate_on_submit() else "No reason provided"
    return H.do_reject(db.get_or_404(PrizePool, item_id), reason, DETAIL)


@prizes_bp.route("/<int:item_id>/winner/<int:winner_id>/toggle-paid", methods=["POST"])
@committee_required
def toggle_paid(item_id, winner_id):
    pp = db.get_or_404(PrizePool, item_id)
    winner = db.get_or_404(PrizeWinner, winner_id)
    if winner.prize_pool_id != pp.id:
        abort(404)
    if pp.status != C.STATUS_APPROVED:
        flash("Winners can be marked paid only after approval.", "danger")
        return redirect(url_for(DETAIL, item_id=pp.id))
    winner.paid = not winner.paid
    winner.paid_at = datetime.utcnow() if winner.paid else None
    record_audit(C.TYPE_PRIZE, pp.id, C.ACTION_SETTLE, current_user,
                 f"Marked {winner.winner_name} as "
                 f"{'paid' if winner.paid else 'unpaid'}.")
    db.session.commit()
    flash(f"{winner.winner_name} marked {'paid' if winner.paid else 'unpaid'}.", "success")
    return redirect(url_for(DETAIL, item_id=pp.id))


@prizes_bp.route("/<int:item_id>/delete", methods=["POST"])
@committee_required
def delete(item_id):
    return H.do_delete(db.get_or_404(PrizePool, item_id), LIST)


@prizes_bp.route("/<int:item_id>/pdf")
@login_required
def pdf(item_id):
    pp = db.get_or_404(PrizePool, item_id)
    buf = prize_pool_pdf(pp)
    return send_file(buf, mimetype="application/pdf", as_attachment=False,
                     download_name=f"prize_pool_{pp.id}.pdf")
