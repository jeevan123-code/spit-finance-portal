"""
Automatic PDF generation with ReportLab.

Produces the four official forms required by the spec, fully populated from
user-entered data — no manual PDF creation needed:

    * Vendor Payment Form
    * Reimbursement Form
    * Prize Pool Form
    * Income & Expenditure Report

Each builder returns a BytesIO ready to stream as an attachment.
"""
from datetime import datetime
from decimal import Decimal
from io import BytesIO

from flask import current_app
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

# Brand palette (mirrors the dark UI accent, but print-friendly on white)
NAVY = colors.HexColor("#0F172A")
SLATE = colors.HexColor("#334155")
GREEN = colors.HexColor("#16A34A")
LIGHT = colors.HexColor("#F1F5F9")
MUTED = colors.HexColor("#64748B")


def _rupees(value):
    value = Decimal(value or 0)
    return f"Rs. {value:,.2f}"


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("OrgTitle", parent=ss["Title"], fontSize=16,
                          textColor=NAVY, spaceAfter=2, leading=20))
    ss.add(ParagraphStyle("OrgSub", parent=ss["Normal"], fontSize=9,
                          textColor=MUTED, spaceAfter=2))
    ss.add(ParagraphStyle("FormTitle", parent=ss["Heading1"], fontSize=13,
                          textColor=GREEN, spaceBefore=8, spaceAfter=8))
    ss.add(ParagraphStyle("Label", parent=ss["Normal"], fontSize=9,
                          textColor=MUTED))
    ss.add(ParagraphStyle("Value", parent=ss["Normal"], fontSize=10,
                          textColor=NAVY))
    ss.add(ParagraphStyle("Small", parent=ss["Normal"], fontSize=8,
                          textColor=MUTED))
    return ss


def _header(story, ss, form_title, ref):
    org = current_app.config.get("ORG_NAME", "Student Council")
    sub = current_app.config.get("ORG_SUBTITLE", "Finance Management Portal")
    story.append(Paragraph(org, ss["OrgTitle"]))
    story.append(Paragraph(sub, ss["OrgSub"]))
    story.append(HRFlowable(width="100%", thickness=1.2, color=GREEN,
                            spaceBefore=4, spaceAfter=6))
    story.append(Paragraph(form_title, ss["FormTitle"]))
    meta = Table(
        [[Paragraph(f"<b>Reference:</b> {ref}", ss["Small"]),
          Paragraph(f"<b>Generated:</b> {datetime.now():%d %b %Y, %I:%M %p}",
                    ss["Small"])]],
        colWidths=[95 * mm, 75 * mm],
    )
    meta.setStyle(TableStyle([("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    story.append(meta)
    story.append(Spacer(1, 6))


def _kv_table(rows, ss):
    """Two-column label/value block."""
    data = [[Paragraph(k, ss["Label"]), Paragraph(str(v), ss["Value"])] for k, v in rows]
    t = Table(data, colWidths=[45 * mm, 125 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LIGHT),
    ]))
    return t


def _items_table(headers, rows, total_label, total_value, ss, col_widths):
    data = [[Paragraph(f"<b>{h}</b>", ss["Value"]) for h in headers]]
    for r in rows:
        data.append([Paragraph(str(c), ss["Value"]) for c in r])
    data.append([""] * (len(headers) - 2)
                + [Paragraph(f"<b>{total_label}</b>", ss["Value"]),
                   Paragraph(f"<b>{total_value}</b>", ss["Value"])])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    last = len(data) - 1
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, last - 1), [colors.white, LIGHT]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, last), (-1, last), colors.HexColor("#DCFCE7")),
        ("ALIGN", (-2, 0), (-1, -1), "RIGHT"),
        ("SPAN", (0, last), (-3, last)) if len(headers) > 2 else ("ALIGN", (0, 0), (0, 0), "LEFT"),
    ]))
    return t


def _signoff(story, ss):
    story.append(Spacer(1, 22))
    cells = []
    for role in ["Committee", "Finance Secretary", "Associate Dean", "Dean"]:
        cells.append(Paragraph(
            f"<para align='center'>______________<br/>"
            f"<font size=8 color='#64748B'>{role}</font></para>", ss["Value"]))
    t = Table([cells], colWidths=[42.5 * mm] * 4)
    t.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 10)]))
    story.append(t)


def _build(form_title, ref, body_builder):
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
        leftMargin=20 * mm, rightMargin=20 * mm, title=form_title,
    )
    ss = _styles()
    story = []
    _header(story, ss, form_title, ref)
    body_builder(story, ss)
    _signoff(story, ss)
    doc.build(story)
    buf.seek(0)
    return buf


# ── Public builders ──────────────────────────────────────────────────────
def vendor_payment_pdf(vp):
    def body(story, ss):
        story.append(_kv_table([
            ("Event", vp.event.name),
            ("Vendor Name", vp.vendor_name),
            ("Invoice No.", vp.invoice_no or "—"),
            ("Status", vp.status_label),
            ("Bank Name", vp.bank_name or "—"),
            ("Account Holder", vp.account_name or "—"),
            ("Account No.", vp.account_no or "—"),
            ("IFSC", vp.ifsc or "—"),
        ], ss))
        story.append(Spacer(1, 10))
        rows = [[i.description, _rupees(i.amount)] for i in vp.items]
        story.append(_items_table(
            ["Description", "Amount"], rows, "Total Payable",
            _rupees(vp.total), ss, col_widths=[130 * mm, 40 * mm]))
    return _build("Vendor Payment Form", f"VP-{vp.id:05d}", body)


def reimbursement_pdf(rb):
    def body(story, ss):
        story.append(_kv_table([
            ("Event", rb.event.name),
            ("Claimant", rb.claimant_name),
            ("Status", rb.status_label),
            ("Bank Name", rb.bank_name or "—"),
            ("Account Holder", rb.account_name or "—"),
            ("Account No.", rb.account_no or "—"),
            ("IFSC", rb.ifsc or "—"),
        ], ss))
        story.append(Spacer(1, 10))
        rows = [[i.description, _rupees(i.amount)] for i in rb.items]
        story.append(_items_table(
            ["Expense Description", "Amount"], rows, "Total Reimbursable",
            _rupees(rb.total), ss, col_widths=[130 * mm, 40 * mm]))
    return _build("Reimbursement Form", f"RB-{rb.id:05d}", body)


def prize_pool_pdf(pp):
    def body(story, ss):
        story.append(_kv_table([
            ("Event", pp.event.name),
            ("Competition", pp.competition_name),
            ("Status", pp.status_label),
            ("Number of Winners", len(pp.winners)),
        ], ss))
        story.append(Spacer(1, 10))
        rows = [[
            f"#{w.position}", w.winner_name,
            f"{w.account_no or '—'} / {w.ifsc or '—'}",
            "Paid" if w.paid else "Pending",
            _rupees(w.prize_amount),
        ] for w in pp.winners]
        story.append(_items_table(
            ["Pos", "Winner", "Account / IFSC", "Payment", "Prize"],
            rows, "Total Prize Pool", _rupees(pp.total), ss,
            col_widths=[14 * mm, 50 * mm, 56 * mm, 22 * mm, 28 * mm]))
    return _build("Prize Pool Disbursement Form", f"PP-{pp.id:05d}", body)


def income_expenditure_pdf(event):
    def body(story, ss):
        story.append(_kv_table([
            ("Event", event.name),
            ("Committee", event.committee_name or "—"),
            ("Venue", event.venue or "—"),
            ("Date", event.event_date.strftime("%d %b %Y") if event.event_date else "—"),
        ], ss))
        story.append(Spacer(1, 10))

        # Income side — approved budgets
        story.append(Paragraph("Sanctioned Budget (Income)", ss["FormTitle"]))
        inc_rows = [[b.title, _rupees(b.total)]
                    for b in event.budgets if b.status == "approved"]
        if not inc_rows:
            inc_rows = [["No approved budgets", _rupees(0)]]
        story.append(_items_table(
            ["Budget Head", "Amount"], inc_rows, "Total Sanctioned",
            _rupees(event.approved_budget), ss, col_widths=[130 * mm, 40 * mm]))

        story.append(Spacer(1, 12))
        story.append(Paragraph("Expenditure", ss["FormTitle"]))
        exp_rows = []
        for vp in event.vendor_payments:
            if vp.status == "approved":
                exp_rows.append([f"Vendor: {vp.vendor_name}", _rupees(vp.total)])
        for rb in event.reimbursements:
            if rb.status == "approved":
                exp_rows.append([f"Reimbursement: {rb.claimant_name}", _rupees(rb.total)])
        for pp in event.prize_pools:
            if pp.status == "approved":
                exp_rows.append([f"Prize: {pp.competition_name}", _rupees(pp.total)])
        if not exp_rows:
            exp_rows = [["No approved expenditure", _rupees(0)]]
        story.append(_items_table(
            ["Expenditure Head", "Amount"], exp_rows, "Total Expenditure",
            _rupees(event.total_expenditure), ss, col_widths=[130 * mm, 40 * mm]))

        story.append(Spacer(1, 12))
        bal = event.balance
        bal_color = "#16A34A" if bal >= 0 else "#DC2626"
        story.append(Paragraph(
            f"<para align='right'><b>Closing Balance: "
            f"<font color='{bal_color}'>{_rupees(bal)}</font></b></para>",
            ss["Value"]))
    return _build("Income & Expenditure Report", f"IE-{event.id:05d}", body)
