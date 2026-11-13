"""Accounting entries for driver money, following the company's process:

1. ADVANCES (start of trip, Dire Dawa, Djibouti...): one bank entry per payment.
       Dr Driver Advances      advance
           Cr Bank                         advance

2. SETTLEMENT (after the accountant checks the receipts):
       Dr Fuel Expense         fuel cost        (truck cost center)
       Dr Road Expenses        road expenses    (truck cost center)
       Dr Driver Allowance     allowance        (truck cost center)
           Cr Driver Advances              advance       (clears the advance)
           Cr Driver Deductions Recovered  deductions    (shortage etc. taken back)
           Cr Bank                         refund to driver   - OR -
       Dr Bank                 refund from driver

Both are created as DRAFT Journal Entries so the accountant reviews and submits them.
"""

import frappe
from frappe import _
from frappe.utils import flt, today

from truck_tms.truck_tms.doctype.transport_settings.transport_settings import get_settings


@frappe.whitelist()
def make_advance_entries(trip):
	"""One draft bank entry for every advance row that is not yet in the accounts."""
	doc = frappe.get_doc("Trip", trip)
	doc.check_permission("read")
	pending = [row for row in doc.advances if not row.journal_entry]
	if not pending:
		frappe.throw(_("All advances of this trip are already recorded"))
	s = get_settings()
	created = []
	for row in pending:
		place = f" at {row.location}" if row.location else ""
		je = new_journal_entry(
			doc,
			_("Driver advance {0}{1} for {2} ({3})").format(row.idx, place, doc.name, doc.driver_name),
			posting_date=row.date,
			reference=row.reference,
		)
		je.append("accounts", {"account": s.driver_advance_account, "debit_in_account_currency": flt(row.amount)})
		je.append("accounts", {"account": s.bank_account, "credit_in_account_currency": flt(row.amount)})
		je.insert()
		frappe.db.set_value("Trip Advance", row.name, "journal_entry", je.name)
		created.append(je.name)
	return created


@frappe.whitelist()
def make_settlement_entry(trip):
	doc = frappe.get_doc("Trip", trip)
	doc.check_permission("read")
	if doc.settlement_journal_entry:
		frappe.throw(_("Settlement entry {0} already exists").format(doc.settlement_journal_entry))
	if not doc.receipts_verified:
		frappe.throw(_("The accountant must check the receipts and tick 'Receipts Checked' first"))
	if flt(doc.total_cost) <= 0:
		frappe.throw(_("Enter the trip costs first"))
	s = get_settings()
	cost_center = frappe.db.get_value("Vehicle", doc.vehicle, "cost_center")

	je = new_journal_entry(doc, _("Trip settlement {0} ({1})").format(doc.name, doc.driver_name))
	for account, amount in expense_totals_by_account(doc, s).items():
		if flt(amount):
			je.append(
				"accounts", {"account": account, "debit_in_account_currency": flt(amount), "cost_center": cost_center}
			)
	if flt(doc.advance_given):
		je.append("accounts", {"account": s.driver_advance_account, "credit_in_account_currency": flt(doc.advance_given)})
	if flt(doc.deduction_total):
		je.append(
			"accounts",
			{
				"account": s.deduction_income_account,
				"credit_in_account_currency": flt(doc.deduction_total),
				"cost_center": cost_center,
			},
		)
	if flt(doc.refund_to_driver):
		je.append("accounts", {"account": s.bank_account, "credit_in_account_currency": flt(doc.refund_to_driver)})
	if flt(doc.refund_to_office):
		je.append("accounts", {"account": s.bank_account, "debit_in_account_currency": flt(doc.refund_to_office)})
	je.insert()
	doc.db_set("settlement_journal_entry", je.name)
	return je.name


def expense_totals_by_account(doc, settings):
	"""Accepted expense lines grouped by account, plus the allowance.
	Each expense type can have its own account; otherwise fuel -> Fuel Expense,
	everything else -> Road Expenses (Transport Settings)."""
	totals = {}
	for row in doc.expenses:
		if row.rejected:
			continue
		account = frappe.db.get_value("Trip Expense Type", row.expense_type, "expense_account") or (
			settings.fuel_expense_account if row.is_fuel else settings.road_expense_account
		)
		totals[account] = totals.get(account, 0) + flt(row.amount)
	if flt(doc.allowance):
		account = settings.allowance_expense_account
		totals[account] = totals.get(account, 0) + flt(doc.allowance)
	return totals


def new_journal_entry(trip, remark, posting_date=None, reference=None):
	posting_date = posting_date or today()
	je = frappe.new_doc("Journal Entry")
	je.update(
		{
			"voucher_type": "Bank Entry",
			"company": trip.company,
			"posting_date": posting_date,
			"cheque_no": reference or trip.name,  # reference shown on the bank line
			"cheque_date": posting_date,
			"user_remark": remark,
		}
	)
	return je
