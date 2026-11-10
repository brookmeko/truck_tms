// Copyright (c) 2026, Biruk and contributors
// For license information, please see license.txt

frappe.query_reports["Driver Settlement Summary"] = {
	filters: [
		{ fieldname: "from_date", label: __("From"), fieldtype: "Date", default: frappe.datetime.add_months(frappe.datetime.get_today(), -1) },
		{ fieldname: "to_date", label: __("To"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "driver", label: __("Driver"), fieldtype: "Link", options: "Driver" },
	],
};
