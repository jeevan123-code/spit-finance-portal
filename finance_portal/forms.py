"""WTForms definitions. Dynamic line items are handled in the templates/JS
and parsed directly from request.form (see blueprints), so forms here cover
the header fields and validation."""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, TextAreaField, DateField, DecimalField,
    SelectField, SubmitField,
)
from wtforms.validators import DataRequired, Email, Optional, Length, NumberRange


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign In")


class EventForm(FlaskForm):
    name = StringField("Event Name", validators=[DataRequired(), Length(max=160)])
    committee_name = StringField("Committee", validators=[Optional(), Length(max=120)])
    venue = StringField("Venue", validators=[Optional(), Length(max=160)])
    event_date = DateField("Event Date", validators=[Optional()])
    description = TextAreaField("Description", validators=[Optional()])
    submit = SubmitField("Save Event")


class BudgetForm(FlaskForm):
    title = StringField("Budget Title", validators=[DataRequired(), Length(max=160)])
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Save Budget")


class AdvanceForm(FlaskForm):
    purpose = StringField("Purpose", validators=[DataRequired(), Length(max=255)])
    requested_for = StringField("Requested For", validators=[Optional(), Length(max=120)])
    amount = DecimalField("Amount (₹)", validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField("Save Advance")


class SettlementForm(FlaskForm):
    settled_amount = DecimalField("Settled Amount (₹)",
                                  validators=[DataRequired(), NumberRange(min=0)])
    settlement_notes = TextAreaField("Settlement Notes", validators=[Optional()])
    submit = SubmitField("Record Settlement")


class VendorPaymentForm(FlaskForm):
    vendor_name = StringField("Vendor Name", validators=[DataRequired(), Length(max=160)])
    invoice_no = StringField("Invoice No.", validators=[Optional(), Length(max=80)])
    bank_name = StringField("Bank Name", validators=[Optional(), Length(max=120)])
    account_name = StringField("Account Holder", validators=[Optional(), Length(max=120)])
    account_no = StringField("Account No.", validators=[Optional(), Length(max=40)])
    ifsc = StringField("IFSC", validators=[Optional(), Length(max=20)])
    submit = SubmitField("Save Vendor Payment")


class ReimbursementForm(FlaskForm):
    claimant_name = StringField("Claimant Name", validators=[DataRequired(), Length(max=160)])
    bank_name = StringField("Bank Name", validators=[Optional(), Length(max=120)])
    account_name = StringField("Account Holder", validators=[Optional(), Length(max=120)])
    account_no = StringField("Account No.", validators=[Optional(), Length(max=40)])
    ifsc = StringField("IFSC", validators=[Optional(), Length(max=20)])
    submit = SubmitField("Save Reimbursement")


class PrizePoolForm(FlaskForm):
    competition_name = StringField("Competition Name",
                                   validators=[DataRequired(), Length(max=160)])
    submit = SubmitField("Save Prize Pool")


class RejectForm(FlaskForm):
    reason = TextAreaField("Reason for rejection", validators=[DataRequired()])
    submit = SubmitField("Reject")


class DocumentForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    category = SelectField("Category", choices=[
        ("bill", "Bill"), ("invoice", "Invoice"), ("receipt", "Receipt"),
        ("supporting", "Supporting Document"),
    ])
    event_id = SelectField("Event", coerce=int, validators=[Optional()])
    submit = SubmitField("Upload")
