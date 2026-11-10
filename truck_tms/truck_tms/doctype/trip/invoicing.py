"""Create Sales Invoices from a Trip's loads.

One invoice per paying load:
  - Freight line:   quantity = quintals, rate = tariff per quintal
  - Demurrage line: quantity = demurrage days, rate = demurrage rate
  - Shortage deducted by the customer -> invoice discount
Invoices are created as DRAFT so finance can review and submit them.
"""

import frappe
from frappe import _
from frappe.utils import flt, today

FREIGHT_ITEM = "Freight Service"
DEMURRAGE_ITEM = "Demurrage"


@frappe.whitelist()
def make_sales_invoices(trip):
	doc = frappe.get_doc("Trip", trip)
	doc.check_permission("read")
	cost_center = frappe.db.get_value("Vehicle", doc.vehicle, "cost_center")
	created = []

	for load in doc.loads:
		if not needs_invoice(load):
			continue
		si = build_invoice(doc, load, cost_center)
		si.insert()
		frappe.db.set_value("Trip Load", load.name, "sales_invoice", si.name)
		created.append(si.name)

	if not created:
		frappe.msgprint(_("No loads need an invoice (already invoiced, empty, owner's cargo, or no customer)."))
	return created


def needs_invoice(load):
	return (
		not load.sales_invoice
		and not load.is_empty_run
		and not load.is_internal_job
		and load.customer
		and flt(load.revenue) > 0
	)


def build_invoice(trip, load, cost_center):
	ensure_service_items()
	route = f"{load.origin} → {load.destination}"
	si = frappe.new_doc("Sales Invoice")
	si.update(
		{
			"customer": load.customer,
			"company": trip.company,
			"posting_date": today(),
			"due_date": today(),
			"trip": trip.name,
			"trip_load": load.name,
			"cost_center": cost_center,
			"remarks": _("{0} ({1}): {2}, truck {3}, driver {4}").format(
				trip.name, load.leg, route, trip.vehicle, trip.driver_name
			),
		}
	)

	if flt(load.quintals) and flt(load.tariff_per_quintal):
		si.append(
			"items",
			{
				"item_code": FREIGHT_ITEM,
				"description": _("Freight {0}, {1} quintals, truck {2}").format(route, load.quintals, trip.vehicle),
				"qty": flt(load.quintals),
				"rate": flt(load.tariff_per_quintal),
				"cost_center": cost_center,
			},
		)
	if flt(load.demurrage_days) and flt(load.demurrage_rate):
		si.append(
			"items",
			{
				"item_code": DEMURRAGE_ITEM,
				"description": _("Demurrage {0} days").format(load.demurrage_days),
				"qty": flt(load.demurrage_days),
				"rate": flt(load.demurrage_rate),
				"cost_center": cost_center,
			},
		)
	if flt(load.shortage_amount):
		si.apply_discount_on = "Grand Total"
		si.discount_amount = flt(load.shortage_amount)
	return si


def ensure_service_items():
	"""Create the two non-stock service items the first time they are needed."""
	for item_code in (FREIGHT_ITEM, DEMURRAGE_ITEM):
		if frappe.db.exists("Item", item_code):
			continue
		item_group = "Services" if frappe.db.exists("Item Group", "Services") else "All Item Groups"
		uom = "Nos" if frappe.db.exists("UOM", "Nos") else frappe.db.get_value("UOM", {}, "name")
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"item_group": item_group,
				"stock_uom": uom,
				"is_stock_item": 0,
				"is_sales_item": 1,
				"is_purchase_item": 0,
			}
		).insert(ignore_permissions=True)
