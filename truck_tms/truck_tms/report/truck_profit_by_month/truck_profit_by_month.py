# Copyright (c) 2026, Biruk and contributors
# For license information, please see license.txt

"""Trips, revenue, cost and net income per truck per month (by trip start date)."""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = get_data(filters)
	return get_columns(), data, None, get_chart(data)


def get_columns():
	cur = {"fieldtype": "Currency", "width": 130}
	return [
		{"label": _("Truck"), "fieldname": "vehicle", "fieldtype": "Link", "options": "Vehicle", "width": 120},
		{"label": _("Month"), "fieldname": "month", "fieldtype": "Data", "width": 90},
		{"label": _("Trips"), "fieldname": "trips", "fieldtype": "Int", "width": 70},
		{"label": _("Revenue"), "fieldname": "revenue", **cur},
		{"label": _("Total Cost"), "fieldname": "cost", **cur},
		{"label": _("Net Income"), "fieldname": "net", **cur},
		{"label": _("Fuel (L)"), "fieldname": "fuel_litres", "fieldtype": "Float", "width": 90},
	]


def get_data(filters):
	conditions = ["docstatus < 2"]
	if filters.from_date:
		conditions.append("start_date >= %(from_date)s")
	if filters.to_date:
		conditions.append("start_date <= %(to_date)s")
	if filters.vehicle:
		conditions.append("vehicle = %(vehicle)s")
	return frappe.db.sql(
		f"""
		select vehicle, date_format(start_date, '%%Y-%%m') as month, count(*) as trips,
			sum(total_revenue) as revenue, sum(total_cost) as cost, sum(net_income) as net,
			sum(fuel_litres) as fuel_litres
		from `tabTrip`
		where {" and ".join(conditions)}
		group by vehicle, month
		order by month desc, vehicle
		""",
		filters,
		as_dict=True,
	)


def get_chart(data):
	"""Bar chart: net income per truck for the whole period."""
	totals = {}
	for row in data:
		totals[row.vehicle] = totals.get(row.vehicle, 0) + flt(row.net)
	if not totals:
		return None
	trucks = sorted(totals, key=totals.get, reverse=True)
	return {
		"data": {"labels": trucks, "datasets": [{"name": _("Net Income"), "values": [totals[t] for t in trucks]}]},
		"type": "bar",
		"fieldtype": "Currency",
	}
