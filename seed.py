"""
Seed the database with demo data: four role accounts, sample events, and
financial requests in every workflow state so the portal looks alive on
first launch.

CLI:        python seed.py            # wipe + reseed, then print accounts
On boot:    seed_if_empty()           # called automatically when AUTO_SEED=1
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

from finance_portal.extensions import db
from finance_portal.models import (
    User, Event, Budget, BudgetItem, Advance, VendorPayment, VendorPaymentItem,
    Reimbursement, ReimbursementItem, PrizePool, PrizeWinner, AuditLog, Notification,
)
from finance_portal import constants as C
from finance_portal.services import record_audit

# Each account has its own distinct password (no shared password).
ACCOUNTS = [
    ("Riya Committee",    "committee@spit.ac.in", C.ROLE_COMMITTEE,  "Cultural Committee", "Committee@SPIT26"),
    ("Finance Secretary", "finance@spit.ac.in",   C.ROLE_FINANCE,     None,                "Finance@SPIT26"),
    ("Associate Dean",    "assocdean@spit.ac.in", C.ROLE_ASSOC_DEAN,  None,                "AssocDean@SPIT26"),
    ("Dean of Students",  "dean@spit.ac.in",      C.ROLE_DEAN,        None,                "Dean@SPIT26"),
]


def make_users():
    users = {}
    for name, email, role, committee, password in ACCOUNTS:
        u = User(name=name, email=email, role=role, committee_name=committee)
        u.set_password(password)
        db.session.add(u)
        users[role] = u
    db.session.flush()
    return users


def make_events(committee):
    events = [
        Event(name="Spectra 2026 — Annual Tech Fest", committee_name="Technical Committee",
              venue="Main Auditorium", event_date=date.today() + timedelta(days=30),
              description="Flagship inter-college technical festival.",
              created_by_id=committee.id),
        Event(name="Aaghaz — Cultural Night", committee_name="Cultural Committee",
              venue="Open Air Theatre", event_date=date.today() + timedelta(days=12),
              description="Annual cultural extravaganza.", created_by_id=committee.id),
        Event(name="Sports Meet 2026", committee_name="Sports Committee",
              venue="College Ground", event_date=date.today() + timedelta(days=50),
              description="Inter-department sports tournament.", created_by_id=committee.id),
    ]
    db.session.add_all(events)
    db.session.flush()
    return events


def _populate():
    """Create all demo rows. Caller must already hold an app context and
    the tables must exist + be empty."""
    users = make_users()
    committee = users[C.ROLE_COMMITTEE]
    events = make_events(committee)
    spectra, aaghaz, sports = events

    # ── Approved budget for Spectra (so dashboards show income) ──────
    b1 = Budget(event_id=spectra.id, title="Stage, Sound & Lighting",
                created_by_id=committee.id, status=C.STATUS_APPROVED)
    b1.items = [
        BudgetItem(category="Stage Setup", description="Truss + backdrop",
                   quantity=1, unit_cost=Decimal("45000")),
        BudgetItem(category="Sound System", description="Line array + mixers",
                   quantity=1, unit_cost=Decimal("38000")),
        BudgetItem(category="Lighting", description="Moving heads x12",
                   quantity=12, unit_cost=Decimal("2500")),
    ]
    db.session.add(b1)

    b2 = Budget(event_id=spectra.id, title="Prize & Hospitality",
                created_by_id=committee.id, status=C.STATUS_APPROVED)
    b2.items = [
        BudgetItem(category="Prize Pool", description="Winner prizes",
                   quantity=1, unit_cost=Decimal("60000")),
        BudgetItem(category="Hospitality", description="Guest stay + meals",
                   quantity=1, unit_cost=Decimal("25000")),
    ]
    db.session.add(b2)

    # ── A budget pending Finance Secretary ───────────────────────────
    b3 = Budget(event_id=aaghaz.id, title="Decoration & Props",
                created_by_id=committee.id, status=C.STATUS_PENDING_FINANCE)
    b3.items = [
        BudgetItem(category="Decor", description="Floral + drapes",
                   quantity=1, unit_cost=Decimal("18000")),
        BudgetItem(category="Props", description="Theme props",
                   quantity=1, unit_cost=Decimal("9500")),
    ]
    db.session.add(b3)

    # ── A budget pending Dean (advanced through the chain) ───────────
    b4 = Budget(event_id=sports.id, title="Equipment & Kits",
                created_by_id=committee.id, status=C.STATUS_PENDING_DEAN)
    b4.items = [
        BudgetItem(category="Equipment", description="Balls, nets, mats",
                   quantity=1, unit_cost=Decimal("22000")),
    ]
    db.session.add(b4)

    # ── Approved vendor payment (expenditure for Spectra) ────────────
    vp = VendorPayment(event_id=spectra.id, vendor_name="Soundwave Audio Rentals",
                       invoice_no="INV-2026-014", bank_name="HDFC Bank",
                       account_name="Soundwave Pvt Ltd", account_no="50100123456789",
                       ifsc="HDFC0001234", created_by_id=committee.id,
                       status=C.STATUS_APPROVED)
    vp.items = [
        VendorPaymentItem(description="Line array hire (3 days)", amount=Decimal("28000")),
        VendorPaymentItem(description="On-site technician", amount=Decimal("6000")),
    ]
    db.session.add(vp)

    # ── Reimbursement pending Associate Dean ─────────────────────────
    rb = Reimbursement(event_id=spectra.id, claimant_name="Aarav Sharma",
                       bank_name="SBI", account_name="Aarav Sharma",
                       account_no="20012345678", ifsc="SBIN0007777",
                       created_by_id=committee.id, status=C.STATUS_PENDING_ASSOC)
    rb.items = [
        ReimbursementItem(description="Printing & banners", amount=Decimal("4200")),
        ReimbursementItem(description="Transport for materials", amount=Decimal("1800")),
    ]
    db.session.add(rb)

    # ── Approved prize pool with winners ─────────────────────────────
    pp = PrizePool(event_id=spectra.id, competition_name="Hackathon Grand Finale",
                   created_by_id=committee.id, status=C.STATUS_APPROVED)
    pp.winners = [
        PrizeWinner(position=1, winner_name="Team Voyager", prize_amount=Decimal("30000"),
                    account_no="111122223333", ifsc="ICIC0004444", paid=True,
                    paid_at=datetime.utcnow()),
        PrizeWinner(position=2, winner_name="Team Nimbus", prize_amount=Decimal("20000"),
                    account_no="444455556666", ifsc="ICIC0004444"),
        PrizeWinner(position=3, winner_name="Team Apex", prize_amount=Decimal("10000"),
                    account_no="777788889999", ifsc="ICIC0004444"),
    ]
    db.session.add(pp)

    # ── Advance pending Finance Secretary ────────────────────────────
    adv = Advance(event_id=aaghaz.id, purpose="Advance for decoration materials",
                  requested_for="Riya Committee", amount=Decimal("15000"),
                  created_by_id=committee.id, status=C.STATUS_PENDING_FINANCE)
    db.session.add(adv)

    # ── A rejected reimbursement (shows the rejected state) ──────────
    rb2 = Reimbursement(event_id=aaghaz.id, claimant_name="Neha Patil",
                        created_by_id=committee.id, status=C.STATUS_REJECTED,
                        rejection_reason="Bills not attached; resubmit with receipts.")
    rb2.items = [ReimbursementItem(description="Misc expenses", amount=Decimal("3000"))]
    db.session.add(rb2)

    db.session.flush()

    # ── Seed audit + notifications for realism ───────────────────────
    record_audit(C.TYPE_BUDGET, b1.id, C.ACTION_APPROVE, users[C.ROLE_DEAN],
                 "Dean approved the Budget.")
    record_audit(C.TYPE_VENDOR, vp.id, C.ACTION_APPROVE, users[C.ROLE_DEAN],
                 "Dean approved the Vendor Payment.")
    record_audit(C.TYPE_PRIZE, pp.id, C.ACTION_APPROVE, users[C.ROLE_DEAN],
                 "Dean approved the Prize Pool.")
    record_audit(C.TYPE_BUDGET, b3.id, C.ACTION_SUBMIT, committee,
                 "Submitted Budget for approval.")

    db.session.add(Notification(
        user_id=users[C.ROLE_FINANCE].id, title="Budget awaiting your approval",
        body="Decoration & Props was submitted by Riya Committee.",
        category="info", link=f"/budgets/{b3.id}"))
    db.session.add(Notification(
        user_id=committee.id, title="Prize Pool fully approved",
        body="Hackathon Grand Finale has completed all approvals.",
        category="success", link=f"/prize-pools/{pp.id}"))

    db.session.commit()


def seed(wipe=True):
    """Populate the database. Caller must be inside an app context."""
    if wipe:
        db.drop_all()
    db.create_all()
    _populate()


def seed_if_empty():
    """Idempotent: create tables and seed demo data only if there are no
    users yet. Safe to call on every boot (used by AUTO_SEED)."""
    db.create_all()
    if User.query.count() == 0:
        _populate()
        return True
    return False


def run():
    from finance_portal import create_app
    app = create_app()
    with app.app_context():
        seed(wipe=True)
    print("✓ Database seeded.")
    print("  Accounts (each has its own password):")
    for name, email, role, committee, password in ACCOUNTS:
        print(f"    {C.ROLE_LABELS[role]:<20} {email:<24} {password}")


if __name__ == "__main__":
    run()
