from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from ..extensions import db
from ..models import Event
from ..forms import EventForm
from ..decorators import committee_required
from ..services import record_audit
from .. import constants as C

events_bp = Blueprint("events", __name__, url_prefix="/events")


@events_bp.route("/")
@login_required
def index():
    events = Event.query.order_by(Event.created_at.desc()).all()
    return render_template("events/list.html", events=events)


@events_bp.route("/<int:event_id>")
@login_required
def detail(event_id):
    event = db.get_or_404(Event, event_id)
    return render_template("events/detail.html", event=event)


@events_bp.route("/new", methods=["GET", "POST"])
@committee_required
def create():
    form = EventForm()
    if form.validate_on_submit():
        event = Event(
            name=form.name.data,
            committee_name=form.committee_name.data or current_user.committee_name,
            venue=form.venue.data,
            event_date=form.event_date.data,
            description=form.description.data,
            created_by_id=current_user.id,
        )
        db.session.add(event)
        db.session.flush()
        record_audit(C.TYPE_BUDGET, event.id, C.ACTION_CREATE, current_user,
                     f"Created event '{event.name}'.")
        db.session.commit()
        flash("Event created.", "success")
        return redirect(url_for("events.detail", event_id=event.id))
    return render_template("events/form.html", form=form, mode="create")


@events_bp.route("/<int:event_id>/edit", methods=["GET", "POST"])
@committee_required
def edit(event_id):
    event = db.get_or_404(Event, event_id)
    form = EventForm(obj=event)
    if form.validate_on_submit():
        form.populate_obj(event)
        db.session.commit()
        flash("Event updated.", "success")
        return redirect(url_for("events.detail", event_id=event.id))
    return render_template("events/form.html", form=form, mode="edit", event=event)
