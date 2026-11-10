# Copyright (c) 2026, Biruk and contributors
# For license information, please see license.txt

"""Daily Truck Report (የደረቅ ጭነት ትራንስፖርት መከታተያ).

Replaces the signed morning Excel sheet: one row per truck showing driver,
route, cargo, current location and stage. Trucks without an active trip show
their truck status (Available = waiting for cargo, In Maintenance, ...).
"""

import frappe
from frappe import _


def execute(filters=None):
	return get_columns(), get_data(filters or {})


def get_columns():
	return [
		{"label": _("Truck"), "fieldname": "vehicle", "fieldtype": "Link", "options": "Vehicle", "width": 110},
		{"label": _("Trailer"), "fieldname": "trailer_plate", "fieldtype": "Data", "width": 90},
		{"label": _("Owner"), "fieldname": "vehicle_owner", "fieldtype": "Data", "width": 120},
		{"label": _("Driver"), "fieldname": "driver_name", "fieldtype": "Data", "width": 150},
		{"label": _("Phone"), "fieldname": "phone", "fieldtype": "Data", "width": 110},
		{"label": _("From"), "fieldname": "origin", "fieldtype": "Link", "options": "Transport Location", "width": 110},
		{"label": _("To"), "fieldname": "destination", "fieldtype": "Link", "options": "Transport Location", "width": 110},
		{"label": _("Cargo"), "fieldname": "cargo_type", "fieldtype": "Link", "options": "Cargo Type", "width": 100},
		{"label": _("Current Location"), "fieldname": "current_location", "fieldtype": "Link", "options": "Transport Location", "width": 120},
		{"label": _("Trip Start"), "fieldname": "start_date", "fieldtype": "Date", "width": 95},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 130},
		{"label": _("Quintals"), "fieldname": "quintals", "fieldtype": "Float", "width": 80},
		{"label": _("Tariff/Qt"), "fieldname": "tariff_per_quintal", "fieldtype": "Currency", "width": 90},
		{"label": _("Stage / Status"), "fieldname": "stage", "fieldtype": "Data", "width": 150},
		{"label": _("Trip"), "fieldname": "trip", "fieldtype": "Link", "options": "Trip", "width": 130},
	]


def get_data(filters):
	vehicles = frappe.get_all(
		"Vehicle",
		filters={"truck_status": ("!=", "Inactive")},
		fields=["name", "trailer_plate", "vehicle_owner", "truck_status"],
		order_by="name",
	)
	rows = []
	for v in vehicles:
		row = {
			"vehicle": v.name,
			"trailer_plate": v.trailer_plate,
			"vehicle_owner": v.vehicle_owner,
			"stage": v.truck_status if v.truck_status != "Available" else _("Available – waiting for cargo"),
		}

		trip = frappe.db.get_value(
			"Trip",
			{"vehicle": v.name, "docstatus": 0, "status": ("in", ("Planned", "In Progress"))},
			["name", "driver", "driver_name", "start_date", "current_location"],
			as_dict=True,
			order_by="start_date desc",
		)
		if trip:
			load = get_active_load(trip.name)
			row.update(
				{
					"trip": trip.name,
					"driver_name": trip.driver_name,
					"phone": frappe.db.get_value("Driver", trip.driver, "cell_number"),
					"start_date": trip.start_date,
					"current_location": trip.current_location,
				}
			)
			if load:
				row.update(
					{
						"origin": load.origin,
						"destination": load.destination,
						"cargo_type": load.cargo_type,
						"customer": load.customer,
						"quintals": load.quintals,
						"tariff_per_quintal": load.tariff_per_quintal,
						"stage": f"{load.stage} ({load.leg})",
					}
				)
		else:
			driver = frappe.db.get_value(
				"Vehicle Driver Assignment", {"vehicle": v.name, "is_active": 1}, "driver"
			)
			if driver:
				row["driver_name"], row["phone"] = frappe.db.get_value("Driver", driver, ["full_name", "cell_number"])
		rows.append(row)
	return rows


def get_active_load(trip):
	"""First load of the trip that is not yet delivered (else the last load)."""
	loads = frappe.get_all(
		"Trip Load",
		filters={"parent": trip, "parenttype": "Trip"},
		fields=["leg", "origin", "destination", "cargo_type", "customer", "quintals", "tariff_per_quintal", "stage"],
		order_by="idx",
	)
	for load in loads:
		if load.stage != "Delivered":
			return load
	return loads[-1] if loads else None
