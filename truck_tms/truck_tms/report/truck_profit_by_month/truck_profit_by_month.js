// Copyright (c) 2026, Biruk and contributors
// For license information, please see license.txt

frappe.query_reports["Truck Profit by Month"] = {
	filters: [
		{ fieldname: "from_date", label: __("From"), fieldtype: "Date", default: frappe.datetime.add_months(frappe.datetime.get_today(), -6) },
		{ fieldname: "to_date", label: __("To"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "vehicle", label: __("Truck"), fieldtype: "Link", options: "Vehicle" },
	],
};
