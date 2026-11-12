// Copyright (c) 2026, Biruk and contributors
// For license information, please see license.txt

frappe.query_reports["Driver Expense Report"] = {
	filters: [
		{ fieldname: "from_date", label: __("From"), fieldtype: "Date", default: frappe.datetime.add_months(frappe.datetime.get_today(), -1), reqd: 1 },
		{ fieldname: "to_date", label: __("To"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "group_by", label: __("Group By"), fieldtype: "Select", options: "Trip\nDriver\nMonth", default: "Trip" },
		{ fieldname: "driver", label: __("Driver"), fieldtype: "Link", options: "Driver" },
		{ fieldname: "vehicle", label: __("Truck"), fieldtype: "Link", options: "Vehicle" },
	],
};
