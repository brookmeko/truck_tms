"""Office staff should only see Truck TMS, not ERPNext, HRMS or the Frappe admin apps.

Admins (System Manager) still see everything. Staff keep their permissions: invoices,
payments and accounting screens stay reachable from the Truck TMS sidebar.
"""

import frappe

TRANSPORT_ROLES = {"Transport Dispatcher", "Transport Manager", "Transport Finance"}
OUR_APP = "truck_tms"

_wrapped = set()


def is_transport_only_user(user=None):
	user = user or frappe.session.user
	if user in ("Administrator", "Guest"):
		return False
	roles = set(frappe.get_roles(user))
	return "System Manager" not in roles and bool(roles & TRANSPORT_ROLES)


def hide_other_apps():
	"""before_request hook: wrap the other apps' apps-screen permission check
	(e.g. erpnext.check_app_permission) so transport staff don't get those apps."""
	for app in frappe.get_installed_apps():
		if app in ("frappe", OUR_APP):
			continue
		for detail in frappe.get_hooks("add_to_apps_screen", app_name=app) or []:
			path = detail.get("has_permission")
			if not path or path in _wrapped:
				continue
			module_name, function_name = path.rsplit(".", 1)
			module = frappe.get_module(module_name)
			original = getattr(module, function_name)

			def check(*args, _original=original, **kwargs):
				if is_transport_only_user():
					return False
				return _original(*args, **kwargs)

			setattr(module, function_name, check)
			_wrapped.add(path)


def restrict_other_desktop_icons():
	"""after_migrate: top-level desktop icons of other apps are shown to System Managers only.
	Icons someone already restricted by hand are left alone."""
	icons = frappe.get_all(
		"Desktop Icon",
		filters={"parent_icon": ("is", "not set")},
		fields=["name", "app"],
	)
	restricted = set(frappe.get_all("Has Role", filters={"parenttype": "Desktop Icon"}, pluck="parent"))
	for icon in icons:
		if icon.app == OUR_APP or icon.name in restricted:
			continue
		frappe.get_doc(
			{
				"doctype": "Has Role",
				"parent": icon.name,
				"parenttype": "Desktop Icon",
				"parentfield": "roles",
				"role": "System Manager",
			}
		).db_insert()

	from frappe.desk.doctype.desktop_icon.desktop_icon import clear_every_users_desktop_icons

	clear_every_users_desktop_icons()


def set_default_app():
	"""Open Truck TMS after login (users can still have their own Default App)."""
	if not frappe.db.get_single_value("System Settings", "default_app"):
		frappe.db.set_single_value("System Settings", "default_app", OUR_APP)
