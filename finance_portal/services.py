"""
Cross-cutting services: audit logging and notifications.

Both are deliberately tiny, single-responsibility helpers so every blueprint
records history and alerts in exactly the same way.
"""
from flask import url_for

from .extensions import db
from .models import AuditLog, Notification, User
from . import constants as C


# ─────────────────────────────────────────────────────────────────────────
#  Audit trail
# ─────────────────────────────────────────────────────────────────────────
def record_audit(entity_type, entity_id, action, actor, detail=""):
    """Append one immutable line to the audit trail. Does NOT commit."""
    log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor_id=actor.id if actor else None,
        detail=detail,
    )
    db.session.add(log)
    return log


def audit_for(entity_type, entity_id):
    return (
        AuditLog.query.filter_by(entity_type=entity_type, entity_id=entity_id)
        .order_by(AuditLog.created_at.desc())
        .all()
    )


# ─────────────────────────────────────────────────────────────────────────
#  Notifications
# ─────────────────────────────────────────────────────────────────────────
def notify(user_id, title, body="", category="info", link=None):
    """Create one notification for a single user. Does NOT commit."""
    n = Notification(
        user_id=user_id, title=title, body=body, category=category, link=link
    )
    db.session.add(n)
    return n


def notify_role(role, title, body="", category="info", link=None):
    """Notify every active user holding a given role."""
    users = User.query.filter_by(role=role, active=True).all()
    for u in users:
        notify(u.id, title, body, category, link)


def unread_count(user_id):
    return Notification.query.filter_by(user_id=user_id, read=False).count()
