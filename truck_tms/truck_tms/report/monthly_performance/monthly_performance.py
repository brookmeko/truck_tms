# Copyright (c) 2026, Biruk and contributors
# For license information, please see license.txt

"""Per truck or per driver, one column per month, for a chosen measure.

Answers questions like:
  - How many trips did each truck make each month this year?
  - How much net income did each driver bring per month?
Measures: Trips, Revenue, Total Cost, Net Income, Fuel (Litres).
"""

import frappe
from frappe import _
from frappe.utils import add_months, flt, get_first_day, getdate

MEASURES = {
	"Trips": ("count(*)", "Int"),
	"Revenue": ("sum(total_revenue)", "Currency"),
	"Total Cost": ("sum(total_cost)", "Currency"),
	"Net Income": ("sum(net_income)", "Currency"),
	"Fuel (Litres)": ("sum(fuel_litres)", "Float"),
}
GROUPS = {"Truck": ("vehicle", "Vehicle"), "Driver": ("driver", "Driver")}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	measure = filters.get("measure") or "Trips"
	group = filters.get("group_by") or "Truck"
	months = get_months(filters.from_date, filters.to_date)
	data = get_data(filters, measure, group, months)
	return get_columns(measure, group, months), data, None, get_chart(data, months, measure)


def get_months(from_date, to_date):
	"""List of 'YYYY-MM' from the month of from_date to the month of to_date."""
	start, end = get_first_day(getdate(from_date)), getdate(to_date)
	months = []
	while start <= end:
		months.append(start.strftime("%Y-%m"))
		start = add_months(start, 1)
	return months


def get_columns(measure, group, months):
	fieldname, doctype = GROUPS[group]
	fieldtype = MEASURES[measure][1]
	columns = [{"label": _(group), "fieldname": "name", "fieldtype": "Link", "options": doctype, "width": 140}]
	if group == "Driver":
		columns.append({"label": _("Driver Name"), "fieldname": "label", "fieldtype": "Data", "width": 150})
	for m in months:
		columns.append({"label": m, "fieldname": m.replace("-", "_"), "fieldtype": fieldtype, "width": 105})
	columns.append({"label": _("Total"), "fieldname": "total", "fieldtype": fieldtype, "width": 120})
	return columns


def get_data(filters, measure, group, months):
	field, _doctype = GROUPS[group]
	expression = MEASURES[measure][0]
	conditions = ["docstatus < 2", "start_date >= %(from_date)s", "start_date <= %(to_date)s"]
	if filters.get("vehicle"):
		conditions.append("vehicle = %(vehicle)s")
	if filters.get("driver"):
		conditions.append("driver = %(driver)s")
	rows = frappe.db.sql(
		f"""select {field} as name, max(driver_name) as label, date_format(start_date, '%%Y-%%m') as month,
			{expression} as value
		from `tabTrip` where {" and ".join(conditions)}
		group by {field}, month""",
		filters,
		as_dict=True,
	)
	table = {}
	for r in rows:
		entry = table.setdefault(r.name, {"name": r.name, "label": r.label, "total": 0})
		entry[r.month.replace("-", "_")] = flt(r.value)
		entry["total"] += flt(r.value)
	for entry in table.values():
		for m in months:
			entry.setdefault(m.replace("-", "_"), 0)
	return sorted(table.values(), key=lambda e: e["total"], reverse=True)


def get_chart(data, months, measure):
	if not data:
		return None
	totals = [sum(flt(row.get(m.replace("-", "_"))) for row in data) for m in months]
	return {
		"data": {"labels": months, "datasets": [{"name": _(measure), "values": totals}]},
		"type": "bar",
		"fieldtype": MEASURES[measure][1],
	}
