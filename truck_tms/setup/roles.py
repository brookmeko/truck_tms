"""Roles, role profiles and permissions on standard ERPNext DocTypes.

Our own DocTypes carry their permissions in their JSON files.
For ERPNext's DocTypes (Vehicle, Driver, Customer, Sales Invoice) we add
Custom DocPerm rows here, so we never edit ERPNext's code.
"""

import frappe
from frappe.permissions import add_permission, update_permission_property

DISPATCHER = "Transport Dispatcher"
MANAGER = "Transport Manager"
FINANCE = "Transport Finance"

ROLES = {
	DISPATCHER: "Creates trips, updates stages and locations, prints the morning report",
	MANAGER: "Approves the morning report, closes (submits) trips, manages trucks and drivers",
	FINANCE: "Invoices, customer payments, driver settlement and deductions",
}

# Role Profile = the bundle of roles you give one kind of user in one click.
ROLE_PROFILES = {
	"Dispatcher": [DISPATCHER],
	"Operations Manager": [DISPATCHER, MANAGER],
	"Finance Officer": [FINANCE, "Accounts User"],
}

# Extra rights on standard DocTypes: {doctype: {role: [rights...]}}
STANDARD_DOCTYPE_PERMS = {
	"Vehicle": {DISPATCHER: ["read"], MANAGER: ["read", "write", "create"], FINANCE: ["read"]},
	"Driver": {DISPATCHER: ["read"], MANAGER: ["read", "write", "create"], FINANCE: ["read"]},
	"Customer": {DISPATCHER: ["read"], MANAGER: ["read", "write", "create"], FINANCE: ["read"]},
	"Sales Invoice": {MANAGER: ["read"], FINANCE: ["read", "write", "create", "submit"]},
}


def create_roles():
	"""Runs BEFORE migrate too, because our DocType permissions refer to these roles."""
	for role, description in ROLES.items():
		if not frappe.db.exists("Role", role):
			frappe.get_doc(
				{"doctype": "Role", "role_name": role, "desk_access": 1, "description": description}
			).insert(ignore_permissions=True)


def setup_roles():
	create_roles()

	for profile, roles in ROLE_PROFILES.items():
		roles = [r for r in roles if frappe.db.exists("Role", r)]
		doc = (
			frappe.get_doc("Role Profile", profile)
			if frappe.db.exists("Role Profile", profile)
			else frappe.new_doc("Role Profile")
		)
		doc.role_profile = profile
		existing = {r.role for r in doc.get("roles", [])}
		for role in roles:
			if role not in existing:
				doc.append("roles", {"role": role})
		doc.save(ignore_permissions=True)

	for doctype, role_rights in STANDARD_DOCTYPE_PERMS.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		for role, rights in role_rights.items():
			if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
				add_permission(doctype, role, 0)
			for right in rights:
				update_permission_property(doctype, role, 0, right, 1)
