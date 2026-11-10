"""Accounting entries for driver money, following the company's process:

1. ADVANCE (before the trip): bank pays the driver.
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
def make_advance_entry(trip):
	doc = frappe.get_doc("Trip", trip)
	doc.check_permission("read")
	if doc.advance_journal_entry:
		frappe.throw(_("Advance entry {0} already exists").format(doc.advance_journal_entry))
	if flt(doc.advance_given) <= 0:
		frappe.throw(_("Enter 'Advance Given to Driver' first"))
	s = get_settings()

	je = new_journal_entry(doc, _("Driver advance for {0} ({1})").format(doc.name, doc.driver_name))
	je.append("accounts", {"account": s.driver_advance_account, "debit_in_account_currency": flt(doc.advance_given)})
	je.append("accounts", {"account": s.bank_account, "credit_in_account_currency": flt(doc.advance_given)})
	je.insert()
	doc.db_set("advance_journal_entry", je.name)
	return je.name


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
	for account, amount in (
		(s.fuel_expense_account, doc.fuel_cost),
		(s.road_expense_account, doc.road_expenses),
		(s.allowance_expense_account, doc.allowance),
	):
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


def new_journal_entry(trip, remark):
	je = frappe.new_doc("Journal Entry")
	je.update(
		{
			"voucher_type": "Bank Entry",
			"company": trip.company,
			"posting_date": today(),
			"cheque_no": trip.name,  # reference shown on the bank line
			"cheque_date": today(),
			"user_remark": remark,
		}
	)
	return je
