# Copyright (c) 2026, Biruk and contributors
# For license information, please see license.txt

"""Driver expenses: fuel, road expenses, allowance, advances and settlement.

Group by:
  Trip   - one row per trip (default)
  Driver - one row per driver for the period
  Month  - one row per driver per month
"""

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	group_by = filters.get("group_by") or "Trip"
	return get_columns(group_by), get_data(filters, group_by)


def get_columns(group_by):
	cur = {"fieldtype": "Currency", "width": 115}
	columns = []
	if group_by == "Trip":
		columns += [
			{"label": _("Start"), "fieldname": "start_date", "fieldtype": "Date", "width": 95},
			{"label": _("Trip"), "fieldname": "trip", "fieldtype": "Link", "options": "Trip", "width": 135},
		]
	if group_by == "Month":
		columns.append({"label": _("Month"), "fieldname": "month", "fieldtype": "Data", "width": 85})
	columns += [
		{"label": _("Driver"), "fieldname": "driver", "fieldtype": "Link", "options": "Driver", "width": 130},
		{"label": _("Driver Name"), "fieldname": "driver_name", "fieldtype": "Data", "width": 150},
	]
	if group_by == "Trip":
		columns.append({"label": _("Truck"), "fieldname": "vehicle", "fieldtype": "Link", "options": "Vehicle", "width": 105})
	else:
		columns.append({"label": _("Trips"), "fieldname": "trips", "fieldtype": "Int", "width": 65})
	columns += [
		{"label": _("Fuel (L)"), "fieldname": "fuel_litres", "fieldtype": "Float", "width": 85},
		{"label": _("Fuel"), "fieldname": "fuel_cost", **cur},
		{"label": _("Road Expenses"), "fieldname": "road_expenses", **cur},
		{"label": _("Allowance"), "fieldname": "allowance", **cur},
		{"label": _("Total Expenses"), "fieldname": "total_cost", **cur},
		{"label": _("Advance Given"), "fieldname": "advance_given", **cur},
		{"label": _("Office Owes Driver"), "fieldname": "refund_to_driver", **cur},
		{"label": _("Driver Returns"), "fieldname": "refund_to_office", **cur},
		{"label": _("Deductions"), "fieldname": "deduction_total", **cur},
	]
	return columns


def get_data(filters, group_by):
	conditions = ["docstatus < 2"]
	if filters.from_date:
		conditions.append("start_date >= %(from_date)s")
	if filters.to_date:
		conditions.append("start_date <= %(to_date)s")
	for field in ("driver", "vehicle"):
		if filters.get(field):
			conditions.append(f"{field} = %({field})s")
	where = " and ".join(conditions)
	money = ["fuel_litres", "fuel_cost", "road_expenses", "allowance", "total_cost", "advance_given",
		"refund_to_driver", "refund_to_office", "deduction_total"]

	if group_by == "Trip":
		return frappe.db.sql(
			f"""select start_date, name as trip, driver, driver_name, vehicle, {", ".join(money)}
			from `tabTrip` where {where} order by start_date desc, name desc""",
			filters,
			as_dict=True,
		)

	sums = ", ".join(f"sum({m}) as {m}" for m in money)
	if group_by == "Month":
		return frappe.db.sql(
			f"""select date_format(start_date, '%%Y-%%m') as month, driver, driver_name, count(*) as trips, {sums}
			from `tabTrip` where {where} group by month, driver, driver_name order by month desc, driver_name""",
			filters,
			as_dict=True,
		)
	return frappe.db.sql(
		f"""select driver, driver_name, count(*) as trips, {sums}
		from `tabTrip` where {where} group by driver, driver_name order by driver_name""",
		filters,
		as_dict=True,
	)
