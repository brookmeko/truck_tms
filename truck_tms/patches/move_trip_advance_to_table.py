"""Trips created before the Advances table had one 'advance_given' number.
Move it into one Trip Advance row so totals and accounting keep working."""

import frappe


def execute():
	trips = frappe.get_all(
		"Trip",
		filters={"advance_given": (">", 0), "docstatus": ("<", 2)},
		fields=["name", "start_date", "advance_given", "advance_journal_entry"],
	)
	for trip in trips:
		if frappe.db.exists("Trip Advance", {"parent": trip.name, "parenttype": "Trip"}):
			continue
		row = frappe.get_doc(
			{
				"doctype": "Trip Advance",
				"parent": trip.name,
				"parenttype": "Trip",
				"parentfield": "advances",
				"idx": 1,
				"date": trip.start_date,
				"amount": trip.advance_given,
				"purpose": "Mixed",
				"payment_method": "Bank Transfer",
				"journal_entry": trip.advance_journal_entry,
			}
		)
		row.db_insert()
