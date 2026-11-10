# Copyright (c) 2026, Biruk and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

REQUIRED = {
	"bank_account": "Bank Account",
	"driver_advance_account": "Driver Advances Account",
	"fuel_expense_account": "Fuel Expense Account",
	"road_expense_account": "Road Expenses Account",
	"allowance_expense_account": "Driver Allowance Account",
	"deduction_income_account": "Driver Deductions Account",
}


class TransportSettings(Document):
	pass


def get_settings():
	"""Return Transport Settings, failing clearly if an account is missing."""
	settings = frappe.get_single("Transport Settings")
	missing = [label for field, label in REQUIRED.items() if not settings.get(field)]
	if missing:
		frappe.throw(
			_("Set these in Transport Settings first: {0}").format(", ".join(missing)),
			title=_("Accounts not configured"),
		)
	return settings
