# Copyright (c) 2026, Biruk and contributors
# For license information, please see license.txt

"""Revenue, costs and net income of every trip in a period."""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	cur = {"fieldtype": "Currency", "width": 115}
	return [
		{"label": _("Trip"), "fieldname": "name", "fieldtype": "Link", "options": "Trip", "width": 135},
		{"label": _("Start"), "fieldname": "start_date", "fieldtype": "Date", "width": 95},
		{"label": _("Truck"), "fieldname": "vehicle", "fieldtype": "Link", "options": "Vehicle", "width": 105},
		{"label": _("Driver"), "fieldname": "driver_name", "fieldtype": "Data", "width": 140},
		{"label": _("Route"), "fieldname": "route", "fieldtype": "Data", "width": 260},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 90},
		{"label": _("Revenue"), "fieldname": "total_revenue", **cur},
		{"label": _("Fuel"), "fieldname": "fuel_cost", **cur},
		{"label": _("Road"), "fieldname": "road_expenses", **cur},
		{"label": _("Allowance"), "fieldname": "allowance", **cur},
		{"label": _("Total Cost"), "fieldname": "total_cost", **cur},
		{"label": _("Net Income"), "fieldname": "net_income", **cur},
		{"label": _("Margin %"), "fieldname": "margin", "fieldtype": "Percent", "width": 85},
	]


def get_conditions(filters):
	conditions = ["t.docstatus < 2"]
	if filters.from_date:
		conditions.append("t.start_date >= %(from_date)s")
	if filters.to_date:
		conditions.append("t.start_date <= %(to_date)s")
	for field in ("vehicle", "driver", "status", "company"):
		if filters.get(field):
			conditions.append(f"t.{field} = %({field})s")
	return " and ".join(conditions)


def get_data(filters):
	rows = frappe.db.sql(
		f"""
		select t.name, t.start_date, t.vehicle, t.driver_name, t.status,
			t.total_revenue, t.fuel_cost, t.road_expenses, t.allowance, t.total_cost, t.net_income,
			(select group_concat(concat(l.origin, ' → ', l.destination) order by l.idx separator ' | ')
				from `tabTrip Load` l where l.parent = t.name and l.parenttype = 'Trip') as route
		from `tabTrip` t
		where {get_conditions(filters)}
		order by t.start_date desc, t.name desc
		""",
		filters,
		as_dict=True,
	)
	for row in rows:
		row.margin = flt(row.net_income) / flt(row.total_revenue) * 100 if flt(row.total_revenue) else 0
	return rows
