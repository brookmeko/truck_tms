"""Create the default accounts for driver money and fill Transport Settings.

Runs after migrate. Only fills settings that are still empty, so anything the
accountant changes is kept. The bank account is NOT created: the accountant
must choose the company's real bank account in Transport Settings.
"""

import frappe
from erpnext import get_default_company

DEFAULTS = [
	# (settings field, account name, root type, account type, preferred parent group)
	("driver_advance_account", "Driver Advances", "Asset", "", "Loans and Advances (Assets)"),
	("fuel_expense_account", "Fuel Expense", "Expense", "", "Direct Expenses"),
	("road_expense_account", "Road Expenses", "Expense", "", "Direct Expenses"),
	("allowance_expense_account", "Driver Allowance", "Expense", "", "Direct Expenses"),
	("deduction_income_account", "Driver Deductions Recovered", "Income", "", "Indirect Income"),
]


def ensure_transport_accounts():
	company = get_default_company()
	if not company or not frappe.db.exists("DocType", "Transport Settings"):
		return
	settings = frappe.get_single("Transport Settings")
	changed = False
	if not settings.company:
		settings.company = company
		changed = True
	for field, account_name, root_type, account_type, parent_name in DEFAULTS:
		if settings.get(field):
			continue
		settings.set(field, get_or_create_account(company, account_name, root_type, account_type, parent_name))
		changed = True
	if not settings.bank_account:
		bank = frappe.db.get_value("Company", company, "default_bank_account")
		if bank:
			settings.bank_account = bank
			changed = True
	if changed:
		settings.save(ignore_permissions=True)


def get_or_create_account(company, account_name, root_type, account_type, parent_name):
	existing = frappe.db.get_value("Account", {"company": company, "account_name": account_name, "is_group": 0})
	if existing:
		return existing
	parent = frappe.db.get_value(
		"Account", {"company": company, "account_name": parent_name, "is_group": 1}
	) or frappe.get_all(
		"Account",
		filters={"company": company, "root_type": root_type, "is_group": 1},
		order_by="lft desc",
		limit=1,
		pluck="name",
	)[0]
	return (
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": account_name,
				"parent_account": parent,
				"company": company,
				"root_type": root_type,
				"account_type": account_type,
				"is_group": 0,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)
