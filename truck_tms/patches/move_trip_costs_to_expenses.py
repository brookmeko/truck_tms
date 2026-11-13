"""Trips created before the Driver Expenses table had single fuel / road amounts.
Turn them into expense lines so the totals keep the same values."""

import frappe

from truck_tms.setup.seed import ensure_expense_types


def execute():
	ensure_expense_types()
	trips = frappe.get_all(
		"Trip",
		filters={"docstatus": ("<", 2)},
		or_filters={"fuel_cost": (">", 0), "road_expenses": (">", 0)},
		fields=["name", "start_date", "fuel_litres", "fuel_cost", "road_expenses"],
	)
	for trip in trips:
		if frappe.db.exists("Trip Expense", {"parent": trip.name, "parenttype": "Trip"}):
			continue
		lines = []
		if trip.fuel_cost:
			lines.append({"expense_type": "Fuel", "is_fuel": 1, "litres": trip.fuel_litres, "amount": trip.fuel_cost})
		if trip.road_expenses:
			lines.append({"expense_type": "Other", "is_fuel": 0, "amount": trip.road_expenses})
		for idx, line in enumerate(lines, start=1):
			frappe.get_doc(
				{
					"doctype": "Trip Expense",
					"parent": trip.name,
					"parenttype": "Trip",
					"parentfield": "expenses",
					"idx": idx,
					"date": trip.start_date,
					"has_receipt": 1,
					"remark": "Moved from the old single amount",
					**line,
				}
			).db_insert()
