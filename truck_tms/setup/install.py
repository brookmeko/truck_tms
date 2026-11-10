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
		],
	}


def setup_custom_fields():
	create_custom_fields(get_custom_fields(), update=True)


def after_install():
	setup_custom_fields()


def after_migrate():
	setup_custom_fields()
