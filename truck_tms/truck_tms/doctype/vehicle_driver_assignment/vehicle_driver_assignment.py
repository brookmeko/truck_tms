# Copyright (c) 2026, Biruk and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime


class VehicleDriverAssignment(Document):
	"""Which driver drives which truck, and when.

	Business rules (requirements 2.4 and rules 1-2):
	- A truck can have only one driver at a time.
	- A driver can drive only one truck at a time.
	- History is kept: ending an assignment sets "To", it is never deleted.
	"""

	def validate(self):
		self.validate_dates()
		self.validate_no_overlap("vehicle", self.vehicle, _("Truck {0} already has driver {1} in {2}"))
		self.validate_no_overlap("driver", self.driver, _("Driver {1} is already assigned to truck {0} in {2}"))
		self.is_active = 0 if self.to_date else 1

	def validate_dates(self):
		if self.to_date and get_datetime(self.to_date) <= get_datetime(self.from_date):
			frappe.throw(_("'To' must be after 'From'"))

	def validate_no_overlap(self, field, value, message):
		"""Two periods overlap when each one starts before the other ends.
		An empty 'To' means the period is still open (ends in the future)."""
		filters = {
			field: value,
			"name": ("!=", self.name),
			"docstatus": ("<", 2),
		}
		for other in frappe.get_all(
			"Vehicle Driver Assignment",
			filters=filters,
			fields=["name", "vehicle", "driver_name", "from_date", "to_date"],
		):
			starts_before_other_ends = other.to_date is None or get_datetime(self.from_date) < get_datetime(other.to_date)
			other_starts_before_this_ends = self.to_date is None or get_datetime(other.from_date) < get_datetime(self.to_date)
			if starts_before_other_ends and other_starts_before_this_ends:
				frappe.throw(message.format(other.vehicle, other.driver_name, other.name), title=_("Already assigned"))


def get_current_driver(vehicle):
	"""Return the Driver currently assigned to a truck, or None. Used later by Trip."""
	return frappe.db.get_value(
		"Vehicle Driver Assignment", {"vehicle": vehicle, "is_active": 1}, "driver"
	)
