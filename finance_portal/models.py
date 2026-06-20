"""
SQLAlchemy data model for the Finance Management Portal.

Design notes
------------
* Every financial request (Budget, Advance, Vendor Payment, Reimbursement,
  Prize Pool) shares a common workflow surface via ``WorkflowMixin``:
  a ``status`` column plus helper properties. This keeps the multi-level
  approval engine completely generic — see ``workflow.py``.
* ``AuditLog`` and ``Notification`` are polymorphic by (entity_type, entity_id)
  so a single table records the history of every request type.
* Money is stored in paise-free Numeric(12, 2) for exact rupee arithmetic.
"""
from datetime import datetime
from decimal import Decimal

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from .extensions import db, login_manager
from . import constants as C


# ─────────────────────────────────────────────────────────────────────────
#  Users & RBAC
# ─────────────────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(40), nullable=False, default=C.ROLE_COMMITTEE)
    committee_name = db.Column(db.String(120))   # e.g. "Cultural Committee"
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # convenience role checks
    @property
    def role_label(self):
        return C.ROLE_LABELS.get(self.role, self.role)

    @property
    def is_committee(self):
        return self.role == C.ROLE_COMMITTEE

    @property
    def is_approver(self):
        return self.role in (C.ROLE_FINANCE, C.ROLE_ASSOC_DEAN, C.ROLE_DEAN)

    @property
    def initials(self):
        parts = self.name.split()
        return ("".join(p[0] for p in parts[:2])).upper() if parts else "?"

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ─────────────────────────────────────────────────────────────────────────
#  Shared workflow surface
# ─────────────────────────────────────────────────────────────────────────
class WorkflowMixin:
    """Adds an approval ``status`` and helpers shared by all request types."""

    status = db.Column(db.String(30), nullable=False, default=C.STATUS_DRAFT, index=True)
    rejection_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def status_label(self):
        return C.STATUS_LABELS.get(self.status, self.status)

    @property
    def badge_class(self):
        return C.STATUS_BADGE.get(self.status, "badge-draft")

    @property
    def is_pending(self):
        return self.status in C.PENDING_STATUSES

    @property
    def is_editable(self):
        # Only drafts (or rejected items, to resubmit) may be edited.
        return self.status in (C.STATUS_DRAFT, C.STATUS_REJECTED)


# ─────────────────────────────────────────────────────────────────────────
#  Events
# ─────────────────────────────────────────────────────────────────────────
class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    venue = db.Column(db.String(160))
    event_date = db.Column(db.Date)
    committee_name = db.Column(db.String(120))
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    created_by = db.relationship("User")

    budgets = db.relationship("Budget", backref="event", cascade="all, delete-orphan")
    advances = db.relationship("Advance", backref="event", cascade="all, delete-orphan")
    vendor_payments = db.relationship("VendorPayment", backref="event", cascade="all, delete-orphan")
    reimbursements = db.relationship("Reimbursement", backref="event", cascade="all, delete-orphan")
    prize_pools = db.relationship("PrizePool", backref="event", cascade="all, delete-orphan")
    documents = db.relationship("Document", backref="event", cascade="all, delete-orphan")

    # ── financial roll-ups ───────────────────────────────────────────────
    @property
    def approved_budget(self):
        return sum(
            (b.total for b in self.budgets if b.status == C.STATUS_APPROVED),
            Decimal("0.00"),
        )

    @property
    def total_expenditure(self):
        """Approved outflows: vendor payments + reimbursements + prize pools."""
        total = Decimal("0.00")
        for vp in self.vendor_payments:
            if vp.status == C.STATUS_APPROVED:
                total += vp.total
        for rb in self.reimbursements:
            if rb.status == C.STATUS_APPROVED:
                total += rb.total
        for pp in self.prize_pools:
            if pp.status == C.STATUS_APPROVED:
                total += pp.total
        return total

    @property
    def balance(self):
        return self.approved_budget - self.total_expenditure

    @property
    def utilisation_pct(self):
        if self.approved_budget <= 0:
            return 0
        return min(100, round(float(self.total_expenditure / self.approved_budget) * 100))

    def __repr__(self):
        return f"<Event {self.name}>"


# ─────────────────────────────────────────────────────────────────────────
#  Budget  (header + dynamic line items)
# ─────────────────────────────────────────────────────────────────────────
class Budget(WorkflowMixin, db.Model):
    __tablename__ = "budgets"
    REQUEST_TYPE = C.TYPE_BUDGET

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    created_by = db.relationship("User")
    items = db.relationship(
        "BudgetItem", backref="budget", cascade="all, delete-orphan", order_by="BudgetItem.id"
    )

    @property
    def total(self):
        return sum((i.amount for i in self.items), Decimal("0.00"))

    @property
    def type_label(self):
        return C.TYPE_LABELS[self.REQUEST_TYPE]


class BudgetItem(db.Model):
    __tablename__ = "budget_items"

    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey("budgets.id"), nullable=False)
    category = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255))
    quantity = db.Column(db.Numeric(10, 2), default=1)
    unit_cost = db.Column(db.Numeric(12, 2), default=0)

    @property
    def amount(self):
        return (self.quantity or 0) * (self.unit_cost or 0)


# ─────────────────────────────────────────────────────────────────────────
#  Advance Requests
# ─────────────────────────────────────────────────────────────────────────
class Advance(WorkflowMixin, db.Model):
    __tablename__ = "advances"
    REQUEST_TYPE = C.TYPE_ADVANCE

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    purpose = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    requested_for = db.Column(db.String(120))   # person receiving the advance
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    # settlement tracking (post-approval reconciliation)
    settled_amount = db.Column(db.Numeric(12, 2), default=0)
    settled_at = db.Column(db.DateTime)
    settlement_notes = db.Column(db.Text)

    created_by = db.relationship("User")

    @property
    def total(self):
        return self.amount or Decimal("0.00")

    @property
    def type_label(self):
        return C.TYPE_LABELS[self.REQUEST_TYPE]

    @property
    def is_settled(self):
        return self.status == C.STATUS_SETTLED


# ─────────────────────────────────────────────────────────────────────────
#  Vendor Payments (header + dynamic entries + bank details)
# ─────────────────────────────────────────────────────────────────────────
class VendorPayment(WorkflowMixin, db.Model):
    __tablename__ = "vendor_payments"
    REQUEST_TYPE = C.TYPE_VENDOR

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    vendor_name = db.Column(db.String(160), nullable=False)
    invoice_no = db.Column(db.String(80))
    # bank details
    bank_name = db.Column(db.String(120))
    account_name = db.Column(db.String(120))
    account_no = db.Column(db.String(40))
    ifsc = db.Column(db.String(20))
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    created_by = db.relationship("User")
    items = db.relationship(
        "VendorPaymentItem", backref="payment", cascade="all, delete-orphan",
        order_by="VendorPaymentItem.id",
    )

    @property
    def total(self):
        return sum((i.amount for i in self.items), Decimal("0.00"))

    @property
    def type_label(self):
        return C.TYPE_LABELS[self.REQUEST_TYPE]


class VendorPaymentItem(db.Model):
    __tablename__ = "vendor_payment_items"

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey("vendor_payments.id"), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(12, 2), default=0)


# ─────────────────────────────────────────────────────────────────────────
#  Reimbursements (header + dynamic entries + bank details)
# ─────────────────────────────────────────────────────────────────────────
class Reimbursement(WorkflowMixin, db.Model):
    __tablename__ = "reimbursements"
    REQUEST_TYPE = C.TYPE_REIMBURSEMENT

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    claimant_name = db.Column(db.String(160), nullable=False)
    # bank details
    bank_name = db.Column(db.String(120))
    account_name = db.Column(db.String(120))
    account_no = db.Column(db.String(40))
    ifsc = db.Column(db.String(20))
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    created_by = db.relationship("User")
    items = db.relationship(
        "ReimbursementItem", backref="reimbursement", cascade="all, delete-orphan",
        order_by="ReimbursementItem.id",
    )

    @property
    def total(self):
        return sum((i.amount for i in self.items), Decimal("0.00"))

    @property
    def type_label(self):
        return C.TYPE_LABELS[self.REQUEST_TYPE]


class ReimbursementItem(db.Model):
    __tablename__ = "reimbursement_items"

    id = db.Column(db.Integer, primary_key=True)
    reimbursement_id = db.Column(db.Integer, db.ForeignKey("reimbursements.id"), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(12, 2), default=0)


# ─────────────────────────────────────────────────────────────────────────
#  Prize Pool (header + winners)
# ─────────────────────────────────────────────────────────────────────────
class PrizePool(WorkflowMixin, db.Model):
    __tablename__ = "prize_pools"
    REQUEST_TYPE = C.TYPE_PRIZE

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    competition_name = db.Column(db.String(160), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    created_by = db.relationship("User")
    winners = db.relationship(
        "PrizeWinner", backref="prize_pool", cascade="all, delete-orphan",
        order_by="PrizeWinner.position",
    )

    @property
    def total(self):
        return sum((w.prize_amount for w in self.winners), Decimal("0.00"))

    @property
    def type_label(self):
        return C.TYPE_LABELS[self.REQUEST_TYPE]


class PrizeWinner(db.Model):
    __tablename__ = "prize_winners"

    id = db.Column(db.Integer, primary_key=True)
    prize_pool_id = db.Column(db.Integer, db.ForeignKey("prize_pools.id"), nullable=False)
    position = db.Column(db.Integer, default=1)        # 1st, 2nd, 3rd ...
    winner_name = db.Column(db.String(160), nullable=False)
    prize_amount = db.Column(db.Numeric(12, 2), default=0)
    paid = db.Column(db.Boolean, default=False)        # payment tracking
    paid_at = db.Column(db.DateTime)
    # bank details for disbursement
    account_no = db.Column(db.String(40))
    ifsc = db.Column(db.String(20))


# ─────────────────────────────────────────────────────────────────────────
#  Document Repository
# ─────────────────────────────────────────────────────────────────────────
class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"))
    category = db.Column(db.String(40), default="supporting")  # bill/invoice/receipt/supporting/generated
    title = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(255), nullable=False)       # stored name on disk
    original_name = db.Column(db.String(255))
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    uploaded_by = db.relationship("User")

    CATEGORY_LABELS = {
        "bill": "Bill",
        "invoice": "Invoice",
        "receipt": "Receipt",
        "supporting": "Supporting Document",
        "generated": "Generated PDF",
    }

    @property
    def category_label(self):
        return self.CATEGORY_LABELS.get(self.category, self.category.title())


# ─────────────────────────────────────────────────────────────────────────
#  Audit Trail  (polymorphic across all request types)
# ─────────────────────────────────────────────────────────────────────────
class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(40), nullable=False)   # constants.TYPE_*
    entity_id = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(30), nullable=False)        # constants.ACTION_*
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    detail = db.Column(db.Text)                              # human-readable summary
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    actor = db.relationship("User")

    @property
    def action_label(self):
        return C.ACTION_LABELS.get(self.action, self.action.title())

    @property
    def type_label(self):
        return C.TYPE_LABELS.get(self.entity_type, self.entity_type)


# ─────────────────────────────────────────────────────────────────────────
#  Notifications
# ─────────────────────────────────────────────────────────────────────────
class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text)
    category = db.Column(db.String(30), default="info")   # info/success/warning/danger
    link = db.Column(db.String(255))                      # deep-link to the entity
    read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship("User")
