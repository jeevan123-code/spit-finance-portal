"""
Shared route helpers for the five financial request blueprints.

Each request type (Budget, Advance, Vendor Payment, Reimbursement, Prize Pool)
exposes the same workflow verbs — submit / approve / reject / delete — so the
logic lives here once and is parameterised by the concrete model.
"""
from decimal import Decimal, InvalidOperation

from flask import flash, redirect, url_for, request, abort
from flask_login import current_user

from ..extensions import db
from ..services import record_audit
from ..workflow import submit as wf_submit, approve as wf_approve, reject as wf_reject, WorkflowError
from .. import constants as C


def to_decimal(raw, default="0"):
    try:
        return Decimal(str(raw).strip() or default)
    except (InvalidOperation, ValueError, AttributeError):
        return Decimal(default)


def can_edit(item):
    """Committee owner may edit drafts/rejected items."""
    return current_user.role == C.ROLE_COMMITTEE and item.is_editable


def do_submit(item, detail_route):
    if current_user.role != C.ROLE_COMMITTEE:
        abort(403)
    try:
        wf_submit(item, current_user)
        flash(f"{item.type_label} submitted for approval.", "success")
    except WorkflowError as e:
        flash(str(e), "danger")
    return redirect(url_for(detail_route, item_id=item.id))


def do_approve(item, detail_route):
    try:
        wf_approve(item, current_user)
        flash(f"{item.type_label} approved.", "success")
    except WorkflowError as e:
        flash(str(e), "danger")
    return redirect(url_for(detail_route, item_id=item.id))


def do_reject(item, reason, detail_route):
    try:
        wf_reject(item, current_user, reason)
        flash(f"{item.type_label} rejected.", "warning")
    except WorkflowError as e:
        flash(str(e), "danger")
    return redirect(url_for(detail_route, item_id=item.id))


def do_delete(item, list_route):
    if not can_edit(item):
        abort(403)
    record_audit(item.REQUEST_TYPE, item.id, C.ACTION_DELETE, current_user,
                 f"Deleted {item.type_label} #{item.id}.")
    db.session.delete(item)
    db.session.commit()
    flash(f"{item.type_label} deleted.", "info")
    return redirect(url_for(list_route))
