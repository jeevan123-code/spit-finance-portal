"""
Application factory for the SPIT Student Council Finance Management Portal.
"""
import os

from flask import Flask, render_template

from .extensions import db, login_manager, csrf
from . import constants as C


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_CONFIG", "default")
    from config import config

    app = Flask(__name__)
    app.config.from_object(config[config_name])
    if hasattr(config[config_name], "init_app"):
        config[config_name].init_app(app)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Auto-seed demo data on first boot (used by free demo hosting).
    if os.environ.get("AUTO_SEED") == "1":
        with app.app_context():
            try:
                from seed import seed_if_empty
                seed_if_empty()
            except Exception as exc:   # never block boot on seeding
                app.logger.warning("AUTO_SEED skipped: %s", exc)

    # Blueprints
    from .blueprints.auth import auth_bp
    from .blueprints.dashboard import dashboard_bp
    from .blueprints.events import events_bp
    from .blueprints.budgets import budgets_bp
    from .blueprints.advances import advances_bp
    from .blueprints.vendors import vendors_bp
    from .blueprints.reimbursements import reimbursements_bp
    from .blueprints.prizes import prizes_bp
    from .blueprints.documents import documents_bp
    from .blueprints.reports import reports_bp
    from .blueprints.notifications import notifications_bp

    for bp in (auth_bp, dashboard_bp, events_bp, budgets_bp, advances_bp,
               vendors_bp, reimbursements_bp, prizes_bp, documents_bp,
               reports_bp, notifications_bp):
        app.register_blueprint(bp)

    # Template globals — make constants + helpers available in every template
    from .services import unread_count
    from flask import url_for

    _DETAIL_ROUTES = {
        C.TYPE_BUDGET: "budgets.detail",
        C.TYPE_ADVANCE: "advances.detail",
        C.TYPE_VENDOR: "vendors.detail",
        C.TYPE_REIMBURSEMENT: "reimbursements.detail",
        C.TYPE_PRIZE: "prizes.detail",
    }

    def detail_link(item):
        route = _DETAIL_ROUTES.get(getattr(item, "REQUEST_TYPE", None))
        return url_for(route, item_id=item.id) if route else "#"

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        ctx = {
            "C": C,
            "ROLE_LABELS": C.ROLE_LABELS,
            "STATUS_LABELS": C.STATUS_LABELS,
            "TYPE_LABELS": C.TYPE_LABELS,
            "detail_link": detail_link,
            "demo_mode": app.config.get("DEMO_MODE", False),
        }
        if current_user.is_authenticated:
            ctx["nav_unread"] = unread_count(current_user.id)
        return ctx

    @app.template_filter("inr")
    def inr(value):
        try:
            return f"₹{float(value):,.2f}"
        except (TypeError, ValueError):
            return "₹0.00"

    @app.template_filter("datefmt")
    def datefmt(value, fmt="%d %b %Y"):
        return value.strftime(fmt) if value else "—"

    # Error pages
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403,
                               message="You don't have permission for this action."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404,
                               message="The page you're looking for doesn't exist."), 404

    @app.errorhandler(401)
    def unauthorized(e):
        return render_template("error.html", code=401,
                               message="Please sign in to continue."), 401

    # CLI helpers
    @app.cli.command("init-db")
    def init_db():
        """Create all tables."""
        db.create_all()
        print("Database tables created.")

    return app
