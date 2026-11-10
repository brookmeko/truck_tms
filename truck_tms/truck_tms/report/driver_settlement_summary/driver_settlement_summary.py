# Copyright (c) 2026, Biruk and contributors
# For license information, please see license.txt

"""Per driver: trips, advances, costs, who owes whom, and deductions still to recover."""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	cur = {"fieldtype": "Currency", "width": 125}
	return [
		{"label": _("Driver"), "fieldname": "driver", "fieldtype": "Link", "options": "Driver", "width": 140},
		{"label": _("Name"), "fieldname": "driver_name", "fieldtype": "Data", "width": 160},
		{"label": _("Trips"), "fieldname": "trips", "fieldtype": "Int", "width": 65},
		{"label": _("Advances Given"), "fieldname": "advance_given", **cur},
		{"label": _("Trip Costs"), "fieldname": "total_cost", **cur},
		{"label": _("Office Owes Driver"), "fieldname": "refund_to_driver", **cur},
		{"label": _("Driver Owes Office"), "fieldname": "refund_to_office", **cur},
		{"label": _("Deducted on Trips"), "fieldname": "deduction_total", **cur},
		{"label": _("Deductions Outstanding"), "fieldname": "deductions_outstanding", **cur},
		{"label": _("Unsettled Trips"), "fieldname": "unsettled", "fieldtype": "Int", "width": 110},
	]


def get_data(filters):
	conditions = ["docstatus < 2"]
	if filters.from_date:
		conditions.append("start_date >= %(from_date)s")
	if filters.to_date:
		conditions.append("start_date <= %(to_date)s")
	if filters.driver:
		conditions.append("driver = %(driver)s")
	rows = frappe.db.sql(
		f"""
		select driver, driver_name, count(*) as trips,
			sum(advance_given) as advance_given, sum(total_cost) as total_cost,
			sum(refund_to_driver) as refund_to_driver, sum(refund_to_office) as refund_to_office,
			sum(deduction_total) as deduction_total,
			sum(case when coalesce(settlement_journal_entry, '') = '' then 1 else 0 end) as unsettled
		from `tabTrip`
		where {" and ".join(conditions)}
		group by driver, driver_name
		order by driver_name
		""",
		filters,
		as_dict=True,
	)
	outstanding = dict(
		frappe.db.sql(
			"""select driver, sum(outstanding_amount) from `tabDriver Deduction`
			where docstatus = 1 group by driver"""
		)
	)
	for row in rows:
		row.deductions_outstanding = flt(outstanding.get(row.driver))
	return rows
