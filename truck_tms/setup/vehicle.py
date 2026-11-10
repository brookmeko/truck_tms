"""Vehicle helpers: one Cost Center per truck, so P&L can be reported per truck."""

import frappe
from erpnext import get_default_company

TRUCKS_GROUP = "Trucks"


def create_cost_center(doc, method=None):
	"""Vehicle after_insert hook."""
	if doc.get("cost_center"):
		return
	company = doc.get("company") or get_default_company()
	if not company:
		return  # setup wizard not done yet
	cost_center = get_or_create_truck_cost_center(doc.name, company)
	doc.db_set("cost_center", cost_center)


def get_or_create_truck_cost_center(plate, company):
	abbr = frappe.get_cached_value("Company", company, "abbr")
	name = f"{plate} - {abbr}"
	if frappe.db.exists("Cost Center", name):
		return name
	parent = get_trucks_group(company, abbr)
	return (
		frappe.get_doc(
			{
				"doctype": "Cost Center",
				"cost_center_name": plate,
				"parent_cost_center": parent,
				"company": company,
				"is_group": 0,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def get_trucks_group(company, abbr):
	"""A 'Trucks' group under the company's root cost center."""
	name = f"{TRUCKS_GROUP} - {abbr}"
	if frappe.db.exists("Cost Center", name):
		return name
	root = frappe.get_all(
		"Cost Center", filters={"company": company, "is_group": 1}, order_by="lft asc", limit=1, pluck="name"
	)[0]
	return (
		frappe.get_doc(
			{
				"doctype": "Cost Center",
				"cost_center_name": TRUCKS_GROUP,
				"parent_cost_center": root,
				"company": company,
				"is_group": 1,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def ensure_vehicle_cost_centers():
	"""Run after migrate: give older vehicles a cost center too."""
	if not get_default_company():
		return
	for name in frappe.get_all("Vehicle", filters={"cost_center": ("in", ("", None))}, pluck="name"):
		create_cost_center(frappe.get_doc("Vehicle", name))
