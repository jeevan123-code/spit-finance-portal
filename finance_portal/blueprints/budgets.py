from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, abort,
)
from flask_login import login_required, current_user

from ..extensions import db
from ..models import Event, Budget, BudgetItem
from ..forms import BudgetForm, RejectForm
from ..decorators import committee_required
from ..services import record_audit, audit_for
from ..workflow import inbox_for
from . import _helpers as H
from .. import constants as C

budgets_bp = Blueprint("budgets", __name__, url_prefix="/budgets")
DETAIL = "budgets.detail"
LIST = "budgets.index"


def _parse_items(budget):
    """Replace a budget's line items from the submitted dynamic rows."""
    categories = request.form.getlist("item_category[]")
    descriptions = request.form.getlist("item_description[]")
    quantities = request.form.getlist("item_qty[]")
    costs = request.form.getlist("item_cost[]")

    for item in list(budget.items):
        db.session.delete(item)

    for cat, desc, qty, cost in zip(categories, descriptions, quantities, costs):
        if not cat.strip():
            continue
        budget.items.append(BudgetItem(
            category=cat.strip(), description=desc.strip(),
            quantity=H.to_decimal(qty, "1"), unit_cost=H.to_decimal(cost, "0"),
        ))


@budgets_bp.route("/")
@login_required
def index():
    if current_user.is_approver:
        budgets = Budget.query.filter(
            Budget.status.in_(C.PENDING_STATUSES + [C.STATUS_APPROVED, C.STATUS_REJECTED])
        ).order_by(Budget.updated_at.desc()).all()
    else:
        budgets = Budget.query.order_by(Budget.updated_at.desc()).all()
    return render_template("budgets/list.html", budgets=budgets,
                           inbox_statuses=inbox_for(current_user))


@budgets_bp.route("/<int:item_id>")
@login_required
def detail(item_id):
    budget = db.get_or_404(Budget, item_id)
    return render_template(
        "budgets/detail.html", budget=budget,
        history=audit_for(C.TYPE_BUDGET, budget.id),
        can_edit=H.can_edit(budget),
        can_act=current_user.is_approver and budget.status in inbox_for(current_user),
        reject_form=RejectForm(),
    )


@budgets_bp.route("/new", methods=["GET", "POST"])
@budgets_bp.route("/new/<int:event_id>", methods=["GET", "POST"])
@committee_required
def create(event_id=None):
    form = BudgetForm()
    events = Event.query.order_by(Event.name).all()
    if request.method == "POST" and form.validate():
        ev_id = request.form.get("event_id", type=int) or event_id
        if not ev_id:
            flash("Please choose an event.", "danger")
            return render_template("budgets/form.html", form=form, events=events,
                                   mode="create", event_id=event_id, budget=None)
        budget = Budget(event_id=ev_id, title=form.title.data,
                        notes=form.notes.data, created_by_id=current_user.id,
                        status=C.STATUS_DRAFT)
        db.session.add(budget)
        _parse_items(budget)
        db.session.flush()
        record_audit(C.TYPE_BUDGET, budget.id, C.ACTION_CREATE, current_user,
                     f"Created budget '{budget.title}' ({budget.total} total).")
        db.session.commit()
        flash("Budget saved as draft.", "success")
        return redirect(url_for(DETAIL, item_id=budget.id))
    return render_template("budgets/form.html", form=form, events=events,
                           mode="create", event_id=event_id, budget=None)


@budgets_bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
@committee_required
def edit(item_id):
    budget = db.get_or_404(Budget, item_id)
    if not H.can_edit(budget):
        abort(403)
    form = BudgetForm(obj=budget)
    events = Event.query.order_by(Event.name).all()
    if request.method == "POST" and form.validate():
        budget.title = form.title.data
        budget.notes = form.notes.data
        _parse_items(budget)
        record_audit(C.TYPE_BUDGET, budget.id, C.ACTION_EDIT, current_user,
                     f"Edited budget '{budget.title}' (now {budget.total} total).")
        db.session.commit()
        flash("Budget updated.", "success")
        return redirect(url_for(DETAIL, item_id=budget.id))
    return render_template("budgets/form.html", form=form, events=events,
                           mode="edit", budget=budget, event_id=budget.event_id)


@budgets_bp.route("/<int:item_id>/submit", methods=["POST"])
@committee_required
def submit(item_id):
    budget = db.get_or_404(Budget, item_id)
    if not budget.items:
        flash("Add at least one line item before submitting.", "danger")
        return redirect(url_for(DETAIL, item_id=budget.id))
    return H.do_submit(budget, DETAIL)


@budgets_bp.route("/<int:item_id>/approve", methods=["POST"])
@login_required
def approve(item_id):
    return H.do_approve(db.get_or_404(Budget, item_id), DETAIL)


@budgets_bp.route("/<int:item_id>/reject", methods=["POST"])
@login_required
def reject(item_id):
    form = RejectForm()
    reason = form.reason.data if form.validate_on_submit() else "No reason provided"
    return H.do_reject(db.get_or_404(Budget, item_id), reason, DETAIL)


@budgets_bp.route("/<int:item_id>/delete", methods=["POST"])
@committee_required
def delete(item_id):
    return H.do_delete(db.get_or_404(Budget, item_id), LIST)
