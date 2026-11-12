# Copyright (c) 2026, Biruk and contributors
# For license information, please see license.txt

"""Payment Follow-up: every paying load that is delivered but not fully paid.

Status of each load:
  Not Invoiced   - unloaded/delivered, no invoice yet
  Draft Invoice  - invoice created but not submitted by finance
  Unpaid         - invoice submitted, nothing paid
  Partly Paid    - part of the invoice paid
  Paid           - fully paid (shown only when 'Include Paid' is ticked)
Days = days since the documents were given to the customer (or unloading / invoice date).
"""

import frappe
from frappe import _
from frappe.utils import date_diff, flt, today

DONE_STAGES = ("Unloading", "Delivered")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 115},
		{"label": _("Days"), "fieldname": "days", "fieldtype": "Int", "width": 65},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 160},
		{"label": _("Phone"), "fieldname": "phone", "fieldtype": "Data", "width": 110},
		{"label": _("Trip"), "fieldname": "trip", "fieldtype": "Link", "options": "Trip", "width": 130},
		{"label": _("Truck"), "fieldname": "vehicle", "fieldtype": "Link", "options": "Vehicle", "width": 100},
		{"label": _("Route"), "fieldname": "route", "fieldtype": "Data", "width": 200},
		{"label": _("Documents Given"), "fieldname": "documents_submitted_date", "fieldtype": "Date", "width": 110},
		{"label": _("Invoice"), "fieldname": "sales_invoice", "fieldtype": "Link", "options": "Sales Invoice", "width": 140},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 115},
		{"label": _("Outstanding"), "fieldname": "outstanding", "fieldtype": "Currency", "width": 115},
	]


def get_data(filters):
	conditions = [
		"t.docstatus < 2",
		"coalesce(l.customer, '') != ''",
		"l.is_empty_run = 0",
		"l.is_internal_job = 0",
		"l.revenue > 0",
		"(l.stage in ('Unloading', 'Delivered') or coalesce(l.sales_invoice, '') != '')",
	]
	if filters.customer:
		conditions.append("l.customer = %(customer)s")
	loads = frappe.db.sql(
		f"""
		select l.customer, l.origin, l.destination, l.revenue, l.shortage_amount, l.sales_invoice,
			l.documents_submitted_date, l.unloading_date, t.name as trip, t.vehicle, t.start_date
		from `tabTrip Load` l join `tabTrip` t on t.name = l.parent and l.parenttype = 'Trip'
		where {" and ".join(conditions)}
		""",
		filters,
		as_dict=True,
	)
	phones = dict(frappe.get_all("Customer", fields=["name", "mobile_no"], as_list=True))
	rows = []
	for load in loads:
		row = {
			"customer": load.customer,
			"phone": phones.get(load.customer),
			"trip": load.trip,
			"vehicle": load.vehicle,
			"route": f"{load.origin} → {load.destination}",
			"documents_submitted_date": load.documents_submitted_date,
			"amount": flt(load.revenue) - flt(load.shortage_amount),
			"outstanding": flt(load.revenue) - flt(load.shortage_amount),
		}
		since = load.documents_submitted_date or load.unloading_date or load.start_date
		invoice = (
			frappe.db.get_value(
				"Sales Invoice",
				load.sales_invoice,
				["name", "docstatus", "grand_total", "outstanding_amount", "posting_date"],
				as_dict=True,
			)
			if load.sales_invoice
			else None
		)
		if not invoice or invoice.docstatus == 2:
			row["status"] = "Not Invoiced"
		elif invoice.docstatus == 0:
			row.update({"status": "Draft Invoice", "sales_invoice": invoice.name, "amount": invoice.grand_total,
				"outstanding": invoice.grand_total})
		else:
			outstanding = flt(invoice.outstanding_amount)
			status = "Paid" if outstanding <= 0 else ("Partly Paid" if outstanding < flt(invoice.grand_total) else "Unpaid")
			row.update({"status": status, "sales_invoice": invoice.name, "amount": invoice.grand_total,
				"outstanding": outstanding})
			since = load.documents_submitted_date or invoice.posting_date
		if row["status"] == "Paid" and not filters.include_paid:
			continue
		if filters.status and row["status"] != filters.status:
			continue
		row["days"] = date_diff(today(), since) if since else 0
		rows.append(row)
	return sorted(rows, key=lambda r: r["days"], reverse=True)
