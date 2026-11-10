"""API for the Truck TMS frontend (Frappe UI app at /tms).

Every function checks the logged-in user's permissions through normal
frappe.get_list / doc.check_permission, so roles from Phase 4.4 apply.
"""

import frappe
from frappe import _
from frappe.utils import flt

from truck_tms.truck_tms.doctype.trip.board import ALL_STAGES, BOARD_COLUMNS, STAGE_TO_COLUMN


@frappe.whitelist()
def get_board():
	"""Active (not yet submitted) trips, each placed in a board column by its active load."""
	trips = frappe.get_list(
		"Trip",
		filters={"docstatus": 0, "status": ("in", ("Planned", "In Progress"))},
		fields=["name", "vehicle", "driver_name", "status", "current_location", "start_date", "total_revenue", "modified"],
		order_by="modified desc",
		limit_page_length=500,
	)
	cards = []
	for trip in trips:
		load = get_active_load(trip.name)
		stage = load.stage if load else "Assigned"
		cards.append(
			{
				**trip,
				"column": STAGE_TO_COLUMN.get(stage, "assigned"),
				"stage": stage,
				"load": load,
				"payment_status": get_payment_status(trip.name),
			}
		)
	return {"columns": BOARD_COLUMNS, "stages": ALL_STAGES, "cards": cards}


def get_active_load(trip):
	loads = frappe.get_all(
		"Trip Load",
		filters={"parent": trip, "parenttype": "Trip"},
		fields=["name", "leg", "origin", "destination", "cargo_type", "customer", "quintals", "stage", "revenue"],
		order_by="idx",
	)
	for load in loads:
		if load.stage != "Delivered":
			return load
	return loads[-1] if loads else None


def get_payment_status(trip):
	"""Unpaid / Partly Paid / Paid across the trip's submitted invoices ('' if none)."""
	invoices = frappe.get_all(
		"Sales Invoice", filters={"trip": trip, "docstatus": 1}, fields=["grand_total", "outstanding_amount"]
	)
	if not invoices:
		return ""
	total = sum(flt(i.grand_total) for i in invoices)
	outstanding = sum(flt(i.outstanding_amount) for i in invoices)
	if outstanding <= 0:
		return "Paid"
	return "Partly Paid" if outstanding < total else "Unpaid"


@frappe.whitelist()
def set_load_stage(trip, load, stage, location=None):
	"""Move one load to a new stage (and optionally update the truck's current location).
	Saving the Trip runs all its rules: dates, stage log, current stage."""
	if stage not in ALL_STAGES:
		frappe.throw(_("Unknown stage: {0}").format(stage))
	doc = frappe.get_doc("Trip", trip)
	doc.check_permission("write")
	row = next((r for r in doc.loads if r.name == load), None)
	if not row:
		frappe.throw(_("Load {0} is not part of trip {1}").format(load, trip))
	row.stage = stage
	if location:
		doc.current_location = location
	if doc.status == "Planned":
		doc.status = "In Progress"
	doc.save()
	return {"trip": doc.name, "current_stage": doc.current_stage}


@frappe.whitelist()
def get_dashboard():
	"""Numbers for the dashboard cards (design B)."""
	vehicles = frappe.get_list("Vehicle", fields=["truck_status"], limit_page_length=1000)
	by_status = {}
	for v in vehicles:
		by_status[v.truck_status or "Available"] = by_status.get(v.truck_status or "Available", 0) + 1
	month_start = frappe.utils.get_first_day(frappe.utils.today())
	if not frappe.has_permission("Trip", "read"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	month = frappe.db.sql(
		"""select sum(total_revenue) as revenue, sum(total_cost) as cost, sum(net_income) as net, count(name) as trips
		from `tabTrip` where docstatus < 2 and start_date >= %s""",
		month_start,
		as_dict=True,
	)[0]
	outstanding = frappe.db.sql(
		"select coalesce(sum(outstanding_amount), 0) from `tabSales Invoice` where docstatus = 1 and trip is not null and trip != ''"
	)[0][0]
	return {
		"trucks_total": len(vehicles),
		"trucks_by_status": by_status,
		"active_trips": frappe.db.count("Trip", {"docstatus": 0, "status": ("in", ("Planned", "In Progress"))}),
		"month": {k: flt(month.get(k)) for k in ("revenue", "cost", "net", "trips")},
		"customer_outstanding": flt(outstanding),
	}

