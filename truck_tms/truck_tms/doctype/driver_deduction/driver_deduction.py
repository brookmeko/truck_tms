# Copyright (c) 2026, Biruk and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class DriverDeduction(Document):
	"""Money a driver owes the company (cargo shortage, unpaid demurrage, damage...).

	Submit = deduction confirmed. It is then recovered on one or more trips:
	add it to a Trip's "Driver Deductions" table; when that Trip is submitted,
	Recovered / Outstanding / Status here update automatically.
	"""

	def validate(self):
		if flt(self.amount) <= 0:
			frappe.throw(_("Amount must be greater than zero"))
		if not self.installments or self.installments < 1:
			self.installments = 1
		self.installment_amount = flt(self.amount) / self.installments
		if self.docstatus == 0:
			self.recovered_amount = 0
			self.outstanding_amount = self.amount
			self.status = "Draft"

	def on_submit(self):
		self.update_recovery()

	def before_cancel(self):
		if flt(self.recovered_amount) > 0:
			frappe.throw(_("Cannot cancel: {0} has already been recovered on trips. Cancel those trips first.").format(
				frappe.format_value(self.recovered_amount, {"fieldtype": "Currency"})
			))

	def on_cancel(self):
		self.db_set("status", "Cancelled")

	def update_recovery(self):
		"""Recovered = sum of this deduction on SUBMITTED trips."""
		recovered = frappe.db.sql(
			"""
			select coalesce(sum(td.amount), 0)
			from `tabTrip Deduction` td
			join `tabTrip` t on t.name = td.parent
			where td.driver_deduction = %s and td.parenttype = 'Trip' and t.docstatus = 1
			""",
			self.name,
		)[0][0]
		outstanding = flt(self.amount) - flt(recovered)
		if flt(recovered) <= 0:
			status = "Unrecovered"
		elif outstanding > 0:
			status = "Partly Recovered"
		else:
			status = "Recovered"
		self.db_set({"recovered_amount": recovered, "outstanding_amount": outstanding, "status": status})


@frappe.whitelist()
def get_outstanding_deductions(driver, exclude=None):
	"""Confirmed deductions of a driver that still have money to recover.
	Suggested amount for this trip = the per-trip installment, capped at what is outstanding."""
	exclude = frappe.parse_json(exclude) if exclude else []
	rows = frappe.get_all(
		"Driver Deduction",
		filters={"driver": driver, "docstatus": 1, "outstanding_amount": (">", 0), "name": ("not in", exclude or [""])},
		fields=["name", "reason", "installment_amount", "outstanding_amount"],
		order_by="posting_date asc",
	)
	for row in rows:
		row.suggested = min(flt(row.installment_amount), flt(row.outstanding_amount))
	return rows
