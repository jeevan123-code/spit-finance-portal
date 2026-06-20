from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, abort, send_file,
)
from flask_login import login_required, current_user

from ..extensions import db
from ..models import Event, Reimbursement, ReimbursementItem
from ..forms import ReimbursementForm, RejectForm
from ..decorators import committee_required
from ..services import record_audit, audit_for
from ..workflow import inbox_for
from ..pdf import reimbursement_pdf
from . import _helpers as H
from .. import constants as C

reimbursements_bp = Blueprint("reimbursements", __name__, url_prefix="/reimbursements")
DETAIL = "reimbursements.detail"
LIST = "reimbursements.index"


def _parse_items(rb):
    descs = request.form.getlist("item_description[]")
    amounts = request.form.getlist("item_amount[]")
    for item in list(rb.items):
        db.session.delete(item)
    for desc, amt in zip(descs, amounts):
        if not desc.strip():
            continue
        rb.items.append(ReimbursementItem(
            description=desc.strip(), amount=H.to_decimal(amt, "0")))


@reimbursements_bp.route("/")
@login_required
def index():
    reimbursements = Reimbursement.query.order_by(Reimbursement.updated_at.desc()).all()
    return render_template("reimbursements/list.html",
                           reimbursements=reimbursements,
                           inbox_statuses=inbox_for(current_user))


@reimbursements_bp.route("/<int:item_id>")
@login_required
def detail(item_id):
    rb = db.get_or_404(Reimbursement, item_id)
    return render_template(
        "reimbursements/detail.html", rb=rb,
        history=audit_for(C.TYPE_REIMBURSEMENT, rb.id),
        can_edit=H.can_edit(rb),
        can_act=current_user.is_approver and rb.status in inbox_for(current_user),
        reject_form=RejectForm(),
    )


@reimbursements_bp.route("/new", methods=["GET", "POST"])
@reimbursements_bp.route("/new/<int:event_id>", methods=["GET", "POST"])
@committee_required
def create(event_id=None):
    form = ReimbursementForm()
    events = Event.query.order_by(Event.name).all()
    if request.method == "POST" and form.validate():
        ev_id = request.form.get("event_id", type=int) or event_id
        if not ev_id:
            flash("Please choose an event.", "danger")
            return render_template("reimbursements/form.html", form=form, events=events,
                                   mode="create", event_id=event_id, rb=None)
        rb = Reimbursement(
            event_id=ev_id, claimant_name=form.claimant_name.data,
            bank_name=form.bank_name.data, account_name=form.account_name.data,
            account_no=form.account_no.data, ifsc=form.ifsc.data,
            created_by_id=current_user.id, status=C.STATUS_DRAFT)
        db.session.add(rb)
        _parse_items(rb)
        db.session.flush()
        record_audit(C.TYPE_REIMBURSEMENT, rb.id, C.ACTION_CREATE, current_user,
                     f"Created reimbursement for '{rb.claimant_name}' ({rb.total}).")
        db.session.commit()
        flash("Reimbursement saved as draft.", "success")
        return redirect(url_for(DETAIL, item_id=rb.id))
    return render_template("reimbursements/form.html", form=form, events=events,
                           mode="create", event_id=event_id, rb=None)


@reimbursements_bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
@committee_required
def edit(item_id):
    rb = db.get_or_404(Reimbursement, item_id)
    if not H.can_edit(rb):
        abort(403)
    form = ReimbursementForm(obj=rb)
    events = Event.query.order_by(Event.name).all()
    if request.method == "POST" and form.validate():
        form.populate_obj(rb)
        _parse_items(rb)
        record_audit(C.TYPE_REIMBURSEMENT, rb.id, C.ACTION_EDIT, current_user,
                     f"Edited reimbursement for '{rb.claimant_name}'.")
        db.session.commit()
        flash("Reimbursement updated.", "success")
        return redirect(url_for(DETAIL, item_id=rb.id))
    return render_template("reimbursements/form.html", form=form, events=events,
                           mode="edit", rb=rb, event_id=rb.event_id)


@reimbursements_bp.route("/<int:item_id>/submit", methods=["POST"])
@committee_required
def submit(item_id):
    rb = db.get_or_404(Reimbursement, item_id)
    if not rb.items:
        flash("Add at least one expense entry before submitting.", "danger")
        return redirect(url_for(DETAIL, item_id=rb.id))
    return H.do_submit(rb, DETAIL)


@reimbursements_bp.route("/<int:item_id>/approve", methods=["POST"])
@login_required
def approve(item_id):
    return H.do_approve(db.get_or_404(Reimbursement, item_id), DETAIL)


@reimbursements_bp.route("/<int:item_id>/reject", methods=["POST"])
@login_required
def reject(item_id):
    form = RejectForm()
    reason = form.reason.data if form.validate_on_submit() else "No reason provided"
    return H.do_reject(db.get_or_404(Reimbursement, item_id), reason, DETAIL)


@reimbursements_bp.route("/<int:item_id>/delete", methods=["POST"])
@committee_required
def delete(item_id):
    return H.do_delete(db.get_or_404(Reimbursement, item_id), LIST)


@reimbursements_bp.route("/<int:item_id>/pdf")
@login_required
def pdf(item_id):
    rb = db.get_or_404(Reimbursement, item_id)
    buf = reimbursement_pdf(rb)
    return send_file(buf, mimetype="application/pdf", as_attachment=False,
                     download_name=f"reimbursement_{rb.id}.pdf")
