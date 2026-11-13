"""Install/migrate hooks for Truck TMS.

Custom fields on standard ERPNext DocTypes are defined here in code, so they
are version-controlled and recreated on every site that installs truck_tms.
"""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def get_custom_fields():
	return {
		"Vehicle": [
			{
				"fieldname": "tms_section",
				"fieldtype": "Section Break",
				"label": "Trucking",
				"insert_after": "model",
			},
			{
				"fieldname": "trailer_plate",
				"fieldtype": "Data",
				"label": "Trailer Plate",
				"insert_after": "tms_section",
				"in_list_view": 1,
				"in_standard_filter": 1,
			},
			{
				"fieldname": "vehicle_owner",
				"fieldtype": "Data",
				"label": "Owner (ባለንብረት)",
				"insert_after": "trailer_plate",
			},
			{
				"fieldname": "tms_column_break",
				"fieldtype": "Column Break",
				"insert_after": "vehicle_owner",
			},
			{
				"fieldname": "truck_status",
				"fieldtype": "Select",
				"label": "Truck Status",
				"options": "Available\nOn Trip\nIn Maintenance\nInactive\nRequisitioned",
				"default": "Available",
				"insert_after": "tms_column_break",
				"in_list_view": 1,
				"in_standard_filter": 1,
			},
			{
				"fieldname": "wialon_unit_id",
				"fieldtype": "Data",
				"label": "Wialon Unit ID",
				"description": "Internal unit id from Wialon (core/search_items), used for GPS sync",
				"insert_after": "truck_status",
				"no_copy": 1,
			},
			{
				"fieldname": "cost_center",
				"fieldtype": "Link",
				"label": "Cost Center",
				"options": "Cost Center",
				"insert_after": "wialon_unit_id",
				"read_only": 1,
				"description": "Created automatically so profit and loss can be reported per truck",
			},
		],
		"Sales Invoice": [
			{
				"fieldname": "trip",
				"fieldtype": "Link",
				"label": "Trip",
				"options": "Trip",
				"insert_after": "customer",
				"read_only": 1,
				"no_copy": 1,
				"in_standard_filter": 1,
			},
			{
				"fieldname": "trip_load",
				"fieldtype": "Data",
				"label": "Trip Load Row",
				"insert_after": "trip",
				"read_only": 1,
				"hidden": 1,
				"no_copy": 1,
			},
		],
	}


def setup_custom_fields():
	create_custom_fields(get_custom_fields(), update=True)


def after_install():
	setup_custom_fields()
	from truck_tms.setup.roles import setup_roles
	from truck_tms.setup.accounts import ensure_transport_accounts

	setup_roles()
	ensure_transport_accounts()
	from truck_tms.setup.seed import ensure_expense_types

	ensure_expense_types()


def after_migrate():
	setup_custom_fields()
	ensure_erpnext_contact_fields()
	from truck_tms.setup.roles import setup_roles
	from truck_tms.setup.accounts import ensure_transport_accounts

	setup_roles()
	ensure_transport_accounts()
	from truck_tms.setup.seed import ensure_expense_types

	ensure_expense_types()
	from truck_tms.setup.vehicle import ensure_vehicle_cost_centers

	ensure_vehicle_cost_centers()


def ensure_erpnext_contact_fields():
	"""ERPNext v16 needs Contact.is_billing_contact to create Sales Invoices.
	On some fresh sites it was missing, so re-run ERPNext's own (idempotent) setup."""
	import frappe

	if not frappe.db.has_column("Contact", "is_billing_contact"):
		from erpnext.setup.install import create_address_and_contact_custom_fields

		create_address_and_contact_custom_fields()
