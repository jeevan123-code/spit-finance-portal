"""
Domain constants: roles, statuses, the approval chain, and request types.

The approval chain is the heart of the system:

    Committee  ->  Finance Secretary  ->  Associate Dean  ->  Dean

A request is created by a Committee member and walks up the chain. Each
approver can APPROVE (advance to the next stage) or REJECT (terminate).
"""

# ── Roles ────────────────────────────────────────────────────────────────
ROLE_COMMITTEE = "committee"
ROLE_FINANCE = "finance_secretary"
ROLE_ASSOC_DEAN = "associate_dean"
ROLE_DEAN = "dean"

ROLES = [ROLE_COMMITTEE, ROLE_FINANCE, ROLE_ASSOC_DEAN, ROLE_DEAN]

ROLE_LABELS = {
    ROLE_COMMITTEE: "Committee",
    ROLE_FINANCE: "Finance Secretary",
    ROLE_ASSOC_DEAN: "Associate Dean",
    ROLE_DEAN: "Dean",
}

# ── Request statuses ─────────────────────────────────────────────────────
STATUS_DRAFT = "draft"
STATUS_PENDING_FINANCE = "pending_finance"
STATUS_PENDING_ASSOC = "pending_assoc"
STATUS_PENDING_DEAN = "pending_dean"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_SETTLED = "settled"   # advances only — money reconciled after approval

STATUS_LABELS = {
    STATUS_DRAFT: "Draft",
    STATUS_PENDING_FINANCE: "Pending · Finance Secretary",
    STATUS_PENDING_ASSOC: "Pending · Associate Dean",
    STATUS_PENDING_DEAN: "Pending · Dean",
    STATUS_APPROVED: "Approved",
    STATUS_REJECTED: "Rejected",
    STATUS_SETTLED: "Settled",
}

# Visual badge class per status (maps to CSS in app.css)
STATUS_BADGE = {
    STATUS_DRAFT: "badge-draft",
    STATUS_PENDING_FINANCE: "badge-pending",
    STATUS_PENDING_ASSOC: "badge-pending",
    STATUS_PENDING_DEAN: "badge-pending",
    STATUS_APPROVED: "badge-approved",
    STATUS_REJECTED: "badge-rejected",
    STATUS_SETTLED: "badge-settled",
}

# ── Approval chain ───────────────────────────────────────────────────────
# Maps the current "pending" status to the role allowed to act and the next
# status on approval. Order encodes the full Committee->Finance->Assoc->Dean.
APPROVAL_CHAIN = {
    STATUS_PENDING_FINANCE: {"role": ROLE_FINANCE, "next": STATUS_PENDING_ASSOC},
    STATUS_PENDING_ASSOC:   {"role": ROLE_ASSOC_DEAN, "next": STATUS_PENDING_DEAN},
    STATUS_PENDING_DEAN:    {"role": ROLE_DEAN, "next": STATUS_APPROVED},
}

# The status a freshly submitted request enters.
INITIAL_PENDING = STATUS_PENDING_FINANCE

PENDING_STATUSES = [STATUS_PENDING_FINANCE, STATUS_PENDING_ASSOC, STATUS_PENDING_DEAN]

# ── Request types (for audit / notifications / polymorphic logging) ──────
TYPE_BUDGET = "budget"
TYPE_ADVANCE = "advance"
TYPE_VENDOR = "vendor_payment"
TYPE_REIMBURSEMENT = "reimbursement"
TYPE_PRIZE = "prize_pool"

TYPE_LABELS = {
    TYPE_BUDGET: "Budget",
    TYPE_ADVANCE: "Advance Request",
    TYPE_VENDOR: "Vendor Payment",
    TYPE_REIMBURSEMENT: "Reimbursement",
    TYPE_PRIZE: "Prize Pool",
}

# ── Audit actions ────────────────────────────────────────────────────────
ACTION_CREATE = "create"
ACTION_EDIT = "edit"
ACTION_DELETE = "delete"
ACTION_SUBMIT = "submit"
ACTION_APPROVE = "approve"
ACTION_REJECT = "reject"
ACTION_SETTLE = "settle"

ACTION_LABELS = {
    ACTION_CREATE: "Created",
    ACTION_EDIT: "Edited",
    ACTION_DELETE: "Deleted",
    ACTION_SUBMIT: "Submitted",
    ACTION_APPROVE: "Approved",
    ACTION_REJECT: "Rejected",
    ACTION_SETTLE: "Settled",
}
