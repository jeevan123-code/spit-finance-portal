from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user

from ..extensions import db
from ..models import Notification

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@notifications_bp.route("/")
@login_required
def index():
    notes = (Notification.query.filter_by(user_id=current_user.id)
             .order_by(Notification.created_at.desc()).limit(100).all())
    return render_template("notifications/list.html", notes=notes)


@notifications_bp.route("/<int:note_id>/open")
@login_required
def open_note(note_id):
    note = db.get_or_404(Notification, note_id)
    if note.user_id == current_user.id:
        note.read = True
        db.session.commit()
    return redirect(note.link or url_for("notifications.index"))


@notifications_bp.route("/read-all", methods=["POST"])
@login_required
def read_all():
    Notification.query.filter_by(user_id=current_user.id, read=False).update(
        {"read": True})
    db.session.commit()
    return redirect(url_for("notifications.index"))
