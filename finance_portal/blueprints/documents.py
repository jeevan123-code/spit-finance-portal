import os
import uuid

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
    current_app, send_from_directory, abort,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import Document, Event
from ..forms import DocumentForm

documents_bp = Blueprint("documents", __name__, url_prefix="/documents")


def _allowed(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


@documents_bp.route("/")
@login_required
def index():
    category = request.args.get("category")
    query = Document.query
    if category:
        query = query.filter_by(category=category)
    documents = query.order_by(Document.uploaded_at.desc()).all()
    return render_template("documents/list.html", documents=documents,
                           active_category=category)


@documents_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    form = DocumentForm()
    form.event_id.choices = [(0, "— No event —")] + [
        (e.id, e.name) for e in Event.query.order_by(Event.name).all()
    ]
    if form.validate_on_submit():
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("Please choose a file to upload.", "danger")
            return render_template("documents/upload.html", form=form)
        if not _allowed(file.filename):
            flash("That file type is not allowed.", "danger")
            return render_template("documents/upload.html", form=form)

        original = secure_filename(file.filename)
        ext = original.rsplit(".", 1)[-1].lower()
        stored = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], stored))

        doc = Document(
            event_id=form.event_id.data or None,
            category=form.category.data,
            title=form.title.data,
            filename=stored,
            original_name=original,
            uploaded_by_id=current_user.id,
        )
        db.session.add(doc)
        db.session.commit()
        flash("Document uploaded.", "success")
        return redirect(url_for("documents.index"))
    return render_template("documents/upload.html", form=form)


@documents_bp.route("/<int:doc_id>/download")
@login_required
def download(doc_id):
    doc = db.get_or_404(Document, doc_id)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"], doc.filename,
        as_attachment=True, download_name=doc.original_name or doc.filename)


@documents_bp.route("/<int:doc_id>/delete", methods=["POST"])
@login_required
def delete(doc_id):
    doc = db.get_or_404(Document, doc_id)
    # Only the uploader or a Dean may delete.
    if doc.uploaded_by_id != current_user.id and current_user.role != "dean":
        abort(403)
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], doc.filename)
    if os.path.exists(path):
        os.remove(path)
    db.session.delete(doc)
    db.session.commit()
    flash("Document deleted.", "info")
    return redirect(url_for("documents.index"))
