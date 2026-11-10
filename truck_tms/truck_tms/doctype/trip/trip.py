# Copyright (c) 2026, Biruk and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

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
		self.validate_truck_not_on_another_trip()
		self.calculate_load_revenue()
		self.calculate_costs()
		self.calculate_summary()
		self.set_current_stage()

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
		self.allowance = flt(self.allowance_base) + flt(self.extra_days) * flt(self.allowance_per_extra_day)
		self.total_cost = flt(self.fuel_cost) + flt(self.road_expenses) + flt(self.allowance)
		difference = flt(self.total_cost) - flt(self.advance_given)
		self.refund_to_driver = difference if difference > 0 else 0
		self.refund_to_office = -difference if difference < 0 else 0

	def calculate_summary(self):
		self.total_revenue = sum(flt(load.revenue) for load in self.loads)
		self.net_income = flt(self.total_revenue) - flt(self.total_cost)

	def set_current_stage(self):
		pending = [load for load in self.loads if load.stage != "Delivered"]
		if pending:
			self.current_stage = f"{pending[0].stage} ({pending[0].leg})"
		elif self.loads:
			self.current_stage = "Delivered"

	# ----- truck status ------------------------------------------------------

	def on_update(self):
		if self.status == "In Progress":
			self.set_truck_status("On Trip")

	def before_submit(self):
		self.status = "Completed"
		if not self.end_date:
			self.end_date = frappe.utils.today()

	def on_submit(self):
		self.set_truck_status("Available")

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		self.set_truck_status("Available")

	def set_truck_status(self, status):
		frappe.db.set_value("Vehicle", self.vehicle, "truck_status", status)


@frappe.whitelist()
def get_vehicle_driver(vehicle):
	"""Called from the form when the truck is chosen."""
	return get_current_driver(vehicle)
