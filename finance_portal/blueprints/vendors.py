from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, abort, send_file,
)
from flask_login import login_required, current_user

from ..extensions import db
from ..models import Event, VendorPayment, VendorPaymentItem
from ..forms import VendorPaymentForm, RejectForm
from ..decorators import committee_required
from ..services import record_audit, audit_for
from ..workflow import inbox_for
from ..pdf import vendor_payment_pdf
from . import _helpers as H
from .. import constants as C

vendors_bp = Blueprint("vendors", __name__, url_prefix="/vendor-payments")
DETAIL = "vendors.detail"
LIST = "vendors.index"


def _parse_items(vp):
    descs = request.form.getlist("item_description[]")
    amounts = request.form.getlist("item_amount[]")
    for item in list(vp.items):
        db.session.delete(item)
    for desc, amt in zip(descs, amounts):
        if not desc.strip():
            continue
        vp.items.append(VendorPaymentItem(
            description=desc.strip(), amount=H.to_decimal(amt, "0")))


@vendors_bp.route("/")
@login_required
def index():
    payments = VendorPayment.query.order_by(VendorPayment.updated_at.desc()).all()
    return render_template("vendors/list.html", payments=payments,
                           inbox_statuses=inbox_for(current_user))


@vendors_bp.route("/<int:item_id>")
@login_required
def detail(item_id):
    vp = db.get_or_404(VendorPayment, item_id)
    return render_template(
        "vendors/detail.html", vp=vp,
        history=audit_for(C.TYPE_VENDOR, vp.id),
        can_edit=H.can_edit(vp),
        can_act=current_user.is_approver and vp.status in inbox_for(current_user),
        reject_form=RejectForm(),
    )


@vendors_bp.route("/new", methods=["GET", "POST"])
@vendors_bp.route("/new/<int:event_id>", methods=["GET", "POST"])
@committee_required
def create(event_id=None):
    form = VendorPaymentForm()
    events = Event.query.order_by(Event.name).all()
    if request.method == "POST" and form.validate():
        ev_id = request.form.get("event_id", type=int) or event_id
        if not ev_id:
            flash("Please choose an event.", "danger")
            return render_template("vendors/form.html", form=form, events=events,
                                   mode="create", event_id=event_id, vp=None)
        vp = VendorPayment(
            event_id=ev_id, vendor_name=form.vendor_name.data,
            invoice_no=form.invoice_no.data, bank_name=form.bank_name.data,
            account_name=form.account_name.data, account_no=form.account_no.data,
            ifsc=form.ifsc.data, created_by_id=current_user.id, status=C.STATUS_DRAFT)
        db.session.add(vp)
        _parse_items(vp)
        db.session.flush()
        record_audit(C.TYPE_VENDOR, vp.id, C.ACTION_CREATE, current_user,
                     f"Created vendor payment to '{vp.vendor_name}' ({vp.total}).")
        db.session.commit()
        flash("Vendor payment saved as draft.", "success")
        return redirect(url_for(DETAIL, item_id=vp.id))
    return render_template("vendors/form.html", form=form, events=events,
                           mode="create", event_id=event_id, vp=None)


@vendors_bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
@committee_required
def edit(item_id):
    vp = db.get_or_404(VendorPayment, item_id)
    if not H.can_edit(vp):
        abort(403)
    form = VendorPaymentForm(obj=vp)
    events = Event.query.order_by(Event.name).all()
    if request.method == "POST" and form.validate():
        form.populate_obj(vp)
        _parse_items(vp)
        record_audit(C.TYPE_VENDOR, vp.id, C.ACTION_EDIT, current_user,
                     f"Edited vendor payment to '{vp.vendor_name}'.")
        db.session.commit()
        flash("Vendor payment updated.", "success")
        return redirect(url_for(DETAIL, item_id=vp.id))
    return render_template("vendors/form.html", form=form, events=events,
                           mode="edit", vp=vp, event_id=vp.event_id)


@vendors_bp.route("/<int:item_id>/submit", methods=["POST"])
@committee_required
def submit(item_id):
    vp = db.get_or_404(VendorPayment, item_id)
    if not vp.items:
        flash("Add at least one payment entry before submitting.", "danger")
        return redirect(url_for(DETAIL, item_id=vp.id))
    return H.do_submit(vp, DETAIL)


@vendors_bp.route("/<int:item_id>/approve", methods=["POST"])
@login_required
def approve(item_id):
    return H.do_approve(db.get_or_404(VendorPayment, item_id), DETAIL)


@vendors_bp.route("/<int:item_id>/reject", methods=["POST"])
@login_required
def reject(item_id):
    form = RejectForm()
    reason = form.reason.data if form.validate_on_submit() else "No reason provided"
    return H.do_reject(db.get_or_404(VendorPayment, item_id), reason, DETAIL)


@vendors_bp.route("/<int:item_id>/delete", methods=["POST"])
@committee_required
def delete(item_id):
    return H.do_delete(db.get_or_404(VendorPayment, item_id), LIST)


@vendors_bp.route("/<int:item_id>/pdf")
@login_required
def pdf(item_id):
    vp = db.get_or_404(VendorPayment, item_id)
    buf = vendor_payment_pdf(vp)
    return send_file(buf, mimetype="application/pdf", as_attachment=False,
                     download_name=f"vendor_payment_{vp.id}.pdf")
