"""
The generic multi-level approval engine.

Every financial request type (Budget, Advance, Vendor Payment, Reimbursement,
Prize Pool) is driven by exactly the same chain:

    Committee  ->  Finance Secretary  ->  Associate Dean  ->  Dean

Because each request model carries a ``status`` and a ``REQUEST_TYPE`` (via
``WorkflowMixin``), this module needs no knowledge of the concrete model — it
only reads/writes ``status`` and emits audit + notification side-effects.
"""
from flask import url_for

from .extensions import db
from .models import User
from .services import record_audit, notify, notify_role
from . import constants as C


class WorkflowError(Exception):
    """Raised when an action is not legal for the current state/role."""


def _deep_link(entity_type, entity_id):
    """Best-effort deep link to a request's detail page."""
    route = {
        C.TYPE_BUDGET: "budgets.detail",
        C.TYPE_ADVANCE: "advances.detail",
        C.TYPE_VENDOR: "vendors.detail",
        C.TYPE_REIMBURSEMENT: "reimbursements.detail",
        C.TYPE_PRIZE: "prizes.detail",
    }.get(entity_type)
    try:
        return url_for(route, item_id=entity_id) if route else None
    except Exception:
        return None


def submit(item, actor):
    """Committee submits a draft/rejected request into the chain."""
    if item.status not in (C.STATUS_DRAFT, C.STATUS_REJECTED):
        raise WorkflowError("Only draft or rejected requests can be submitted.")

    item.status = C.INITIAL_PENDING
    item.rejection_reason = None
    label = C.TYPE_LABELS[item.REQUEST_TYPE]

    record_audit(item.REQUEST_TYPE, item.id, C.ACTION_SUBMIT, actor,
                 f"Submitted {label} for approval.")
    # Alert the first approver tier.
    notify_role(
        C.ROLE_FINANCE,
        title=f"New {label} awaiting your approval",
        body=f"{label} #{item.id} was submitted by {actor.name}.",
        category="info",
        link=_deep_link(item.REQUEST_TYPE, item.id),
    )
    db.session.commit()


def approve(item, actor):
    """Advance the request one stage. Validates the actor owns this stage."""
    stage = C.APPROVAL_CHAIN.get(item.status)
    if stage is None:
        raise WorkflowError("This request is not awaiting approval.")
    if actor.role != stage["role"]:
        raise WorkflowError(
            f"Only the {C.ROLE_LABELS[stage['role']]} can approve at this stage."
        )

    next_status = stage["next"]
    item.status = next_status
    label = C.TYPE_LABELS[item.REQUEST_TYPE]
    link = _deep_link(item.REQUEST_TYPE, item.id)

    record_audit(item.REQUEST_TYPE, item.id, C.ACTION_APPROVE, actor,
                 f"{actor.role_label} approved the {label}.")

    if next_status == C.STATUS_APPROVED:
        # Fully approved — tell the creator it's cleared.
        if item.created_by_id:
            notify(item.created_by_id,
                   title=f"{label} fully approved",
                   body=f"Your {label} #{item.id} has completed all approvals.",
                   category="success", link=link)
    else:
        # Notify the next approver tier.
        next_role = C.APPROVAL_CHAIN[next_status]["role"]
        notify_role(
            next_role,
            title=f"{label} awaiting your approval",
            body=f"{label} #{item.id} was approved by {actor.role_label}.",
            category="info", link=link,
        )
        if item.created_by_id:
            notify(item.created_by_id,
                   title=f"{label} approved by {actor.role_label}",
                   body=f"Your {label} #{item.id} advanced to "
                        f"{C.STATUS_LABELS[next_status]}.",
                   category="info", link=link)
    db.session.commit()


def reject(item, actor, reason):
    """Reject at the current stage. Terminates the chain."""
    stage = C.APPROVAL_CHAIN.get(item.status)
    if stage is None:
        raise WorkflowError("This request is not awaiting approval.")
    if actor.role != stage["role"]:
        raise WorkflowError(
            f"Only the {C.ROLE_LABELS[stage['role']]} can reject at this stage."
        )

    item.status = C.STATUS_REJECTED
    item.rejection_reason = reason
    label = C.TYPE_LABELS[item.REQUEST_TYPE]
    link = _deep_link(item.REQUEST_TYPE, item.id)

    record_audit(item.REQUEST_TYPE, item.id, C.ACTION_REJECT, actor,
                 f"{actor.role_label} rejected the {label}: {reason}")
    if item.created_by_id:
        notify(item.created_by_id,
               title=f"{label} rejected",
               body=f"Your {label} #{item.id} was rejected by "
                    f"{actor.role_label}. Reason: {reason}",
               category="danger", link=link)
    db.session.commit()


def inbox_for(actor):
    """Return the set of statuses this role is responsible for approving."""
    return [s for s, cfg in C.APPROVAL_CHAIN.items() if cfg["role"] == actor.role]
