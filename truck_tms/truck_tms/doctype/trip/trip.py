# Copyright (c) 2026, Biruk and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from truck_tms.truck_tms.doctype.trip.board import LABEL_TO_COLUMN, STAGE_TO_LABEL
from truck_tms.truck_tms.doctype.vehicle_driver_assignment.vehicle_driver_assignment import (
	get_current_driver,
)

ACTIVE_STATUSES = ("Planned", "In Progress")


class Trip(Document):
	"""One round trip of one truck (e.g. Addis -> Djibouti -> Addis).

	- Costs (fuel, road expenses, allowance) belong to the whole trip.
	- Revenue belongs to each load (leg) in the `loads` table.
	- Draft = trip running. Submit = trip closed and settled (figures locked).
	"""

	def validate(self):
		self.set_driver_from_assignment()
		self.validate_dates()
		self.apply_board_column_change()
		self.validate_truck_not_on_another_trip()
		self.set_stage_dates()
		self.calculate_load_revenue()
		self.validate_deductions()
		self.validate_advances()
		self.calculate_costs()
		self.calculate_summary()
		self.set_current_stage()
		self.set_board_column()
		self.set_receipts_verified_by()
		self.validate_expense_lock()

	def before_update_after_submit(self):
		self.set_receipts_verified_by()

	def validate_expense_lock(self):
		"""The dispatcher types in the driver's expense form. Once the accountant has
		ticked Receipts Checked, only finance can change the lines."""
		before = self.get_doc_before_save()
		if not before or not before.receipts_verified or can_check_receipts():
			return

		def lines(doc):
			return [
				(r.date and str(r.date), r.expense_type, flt(r.litres), flt(r.amount), r.receipt_no, r.receipt)
				for r in doc.expenses
			]

		if lines(before) != lines(self):
			frappe.throw(
				_("Receipts are already checked by finance. Ask the accountant to untick Receipts Checked before changing expenses."),
				title=_("Expenses locked"),
			)

	def set_receipts_verified_by(self):
		self.receipts_verified_by = (self.receipts_verified_by or frappe.session.user) if self.receipts_verified else None

	# ----- defaults & checks -------------------------------------------------

	def set_driver_from_assignment(self):
		if not self.driver and self.vehicle:
			self.driver = get_current_driver(self.vehicle)
		if not self.driver:
			frappe.throw(_("Truck {0} has no active driver. Create a Vehicle Driver Assignment first.").format(self.vehicle))

	def validate_dates(self):
		if self.end_date and getdate(self.end_date) < getdate(self.start_date):
			frappe.throw(_("End Date cannot be before Start Date"))

	def validate_truck_not_on_another_trip(self):
		"""Business rule 1: a truck cannot be on two active trips at the same time."""
		if self.status not in ACTIVE_STATUSES:
			return
		other = frappe.db.get_value(
			"Trip",
			{
				"vehicle": self.vehicle,
				"name": ("!=", self.name),
				"docstatus": 0,
				"status": ("in", ACTIVE_STATUSES),
			},
			"name",
		)
		if other:
			frappe.throw(_("Truck {0} is already on active trip {1}").format(self.vehicle, other), title=_("Truck busy"))

	# ----- stages ------------------------------------------------------------

	STAGE_DATE_FIELDS = {
		"Loading": "loading_date",
		"Border Crossing": "border_crossing_date",
		"At Customs": "customs_in_date",
		"Unloading": "unloading_date",
	}
	AFTER_CUSTOMS = ("Waiting Unload Place", "Unload Queue", "Unloading", "Delivered")

	def set_stage_dates(self):
		"""Fill a load's date automatically the first time it reaches a stage."""
		today = frappe.utils.today()
		for load in self.loads:
			field = self.STAGE_DATE_FIELDS.get(load.stage)
			if field and not load.get(field):
				load.set(field, today)
			if load.stage in self.AFTER_CUSTOMS and load.customs_in_date and not load.customs_out_date:
				load.customs_out_date = today

	def log_stage_changes(self):
		"""Write a Trip Stage Log row for every stage or location change (rule 9)."""
		before = self.get_doc_before_save()
		old_stages = {row.name: row.stage for row in before.loads} if before else {}
		location_changed = bool(before) and before.current_location != self.current_location
		logged = False

		for load in self.loads:
			old = old_stages.get(load.name)
			if old is None and load.stage == "Assigned":
				continue  # new row at its starting stage: nothing to log
			if old != load.stage:
				self.add_stage_log(load.leg, old, load.stage)
				logged = True

		if location_changed and not logged:
			stage = self.current_stage or ""
			self.add_stage_log("", stage, stage)

	def add_stage_log(self, leg, from_stage, to_stage):
		frappe.get_doc(
			{
				"doctype": "Trip Stage Log",
				"trip": self.name,
				"vehicle": self.vehicle,
				"leg": leg,
				"from_stage": from_stage,
				"to_stage": to_stage,
				"location": self.current_location,
				"changed_on": frappe.utils.now_datetime(),
				"changed_by": frappe.session.user,
			}
		).insert(ignore_permissions=True)

	# ----- driver deductions -------------------------------------------------

	def validate_deductions(self):
		"""Each row must be a confirmed deduction of THIS trip's driver, and not more than what is outstanding."""
		seen = set()
		for row in self.deductions:
			if row.driver_deduction in seen:
				frappe.throw(_("Row {0}: deduction {1} is listed twice").format(row.idx, row.driver_deduction))
			seen.add(row.driver_deduction)
			ded = frappe.db.get_value(
				"Driver Deduction",
				row.driver_deduction,
				["driver", "docstatus", "outstanding_amount", "reason"],
				as_dict=True,
			)
			if ded.docstatus != 1:
				frappe.throw(_("Row {0}: deduction {1} is not submitted yet").format(row.idx, row.driver_deduction))
			if ded.driver != self.driver:
				frappe.throw(_("Row {0}: deduction {1} belongs to another driver").format(row.idx, row.driver_deduction))
			if flt(row.amount) <= 0 or flt(row.amount) > flt(ded.outstanding_amount):
				frappe.throw(
					_("Row {0}: amount must be between 0 and the outstanding {1}").format(
						row.idx, frappe.format_value(ded.outstanding_amount, {"fieldtype": "Currency"})
					)
				)
			row.reason = ded.reason
		self.deduction_total = sum(flt(row.amount) for row in self.deductions)

	def update_deduction_recovery(self):
		for row in self.deductions:
			frappe.get_doc("Driver Deduction", row.driver_deduction).update_recovery()

	# ----- advances ------------------------------------------------------------

	def validate_advances(self):
		"""Every payment to the driver is a row. A row already posted to the accounts
		(has a Journal Entry) cannot be removed or changed."""
		for row in self.advances:
			if flt(row.amount) <= 0:
				frappe.throw(_("Advances row {0}: amount must be greater than zero").format(row.idx))
		before = self.get_doc_before_save()
		if not before:
			return
		current = {row.name: row for row in self.advances}
		for old in before.advances:
			if not old.journal_entry:
				continue
			new = current.get(old.name)
			if not new or flt(new.amount) != flt(old.amount) or new.journal_entry != old.journal_entry:
				frappe.throw(
					_("Advance of {0} is already recorded in accounts ({1}). Cancel that journal entry first.").format(
						frappe.format_value(old.amount, {"fieldtype": "Currency"}), old.journal_entry
					)
				)

	# ----- calculations ------------------------------------------------------

	def calculate_load_revenue(self):
		"""Revenue = quintals x tariff per quintal + demurrage days x demurrage rate.
		Empty runs and the owner's own cargo earn no revenue."""
		for load in self.loads:
			if load.is_empty_run or load.is_internal_job:
				load.revenue = 0
				continue
			load.revenue = flt(load.quintals) * flt(load.tariff_per_quintal) + flt(load.demurrage_days) * flt(
				load.demurrage_rate
			)

	def calculate_costs(self):
		"""Allowance = base + extra days x per-day amount.
		Total cost = fuel + road expenses + allowance.
		Settlement: compare total cost with the advance given to the driver."""
		self.advance_given = sum(flt(row.amount) for row in self.advances)
		self.calculate_expense_totals()
		self.allowance = flt(self.allowance_base) + flt(self.extra_days) * flt(self.allowance_per_extra_day)
		self.total_cost = flt(self.fuel_cost) + flt(self.road_expenses) + flt(self.allowance)
		# Deductions are money the driver owes, so they reduce what the office pays him.
		difference = flt(self.total_cost) - flt(self.advance_given) - flt(self.deduction_total)
		self.refund_to_driver = difference if difference > 0 else 0
		self.refund_to_office = -difference if difference < 0 else 0

	def calculate_expense_totals(self):
		"""Totals from the driver's expense form. Rejected lines are not paid to the driver."""
		for row in self.expenses:
			# fetched fields are filled after validate, so read the flag here
			row.is_fuel = frappe.get_cached_value("Trip Expense Type", row.expense_type, "is_fuel") or 0
			if not row.is_fuel:
				row.litres = 0
			if flt(row.amount) <= 0:
				frappe.throw(_("Expenses row {0}: amount must be greater than zero").format(row.idx))
		accepted = [row for row in self.expenses if not row.rejected]
		self.fuel_cost = sum(flt(r.amount) for r in accepted if r.is_fuel)
		self.fuel_litres = sum(flt(r.litres) for r in accepted if r.is_fuel)
		self.road_expenses = sum(flt(r.amount) for r in accepted if not r.is_fuel)
		self.rejected_expenses = sum(flt(r.amount) for r in self.expenses if r.rejected)

	def calculate_summary(self):
		self.total_revenue = sum(flt(load.revenue) for load in self.loads)
		self.net_income = flt(self.total_revenue) - flt(self.total_cost)

	def apply_board_column_change(self):
		"""Card dragged to another column on the Operations Board:
		move the active load to the first stage of that column (Settlement = Delivered)."""
		before = self.get_doc_before_save()
		if not before or not self.board_column or before.board_column == self.board_column:
			return
		active = next((load for load in self.loads if load.stage != "Delivered"), None)
		column = LABEL_TO_COLUMN.get(self.board_column)
		if active and column:
			active.stage = column["stages"][0]

	def set_board_column(self):
		active = next((load for load in self.loads if load.stage != "Delivered"), None)
		self.board_column = STAGE_TO_LABEL.get(active.stage, "Assigned") if active else "Settlement"

	def set_current_stage(self):
		pending = [load for load in self.loads if load.stage != "Delivered"]
		if pending:
			self.current_stage = f"{pending[0].stage} ({pending[0].leg})"
		elif self.loads:
			self.current_stage = "Delivered"

	# ----- truck status ------------------------------------------------------

	def on_update(self):
		self.log_stage_changes()
		if self.status == "In Progress":
			self.set_truck_status("On Trip")

	def before_submit(self):
		self.status = "Completed"
		if not self.end_date:
			self.end_date = frappe.utils.today()

	def on_submit(self):
		self.set_truck_status("Available")
		self.update_deduction_recovery()

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		self.set_truck_status("Available")
		self.update_deduction_recovery()

	def set_truck_status(self, status):
		frappe.db.set_value("Vehicle", self.vehicle, "truck_status", status)


@frappe.whitelist()
def get_vehicle_driver(vehicle):
	"""Called from the form when the truck is chosen."""
	return get_current_driver(vehicle)


FINANCE_ROLES = {"Transport Finance", "Transport Manager", "System Manager"}


def can_check_receipts(user=None):
	user = user or frappe.session.user
	return user == "Administrator" or bool(FINANCE_ROLES & set(frappe.get_roles(user)))
