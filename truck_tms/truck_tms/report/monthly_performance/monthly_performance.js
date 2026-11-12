// Copyright (c) 2026, Biruk and contributors
// For license information, please see license.txt

frappe.query_reports["Monthly Performance"] = {
	filters: [
		{ fieldname: "from_date", label: __("From"), fieldtype: "Date", default: frappe.datetime.add_months(frappe.datetime.get_today(), -11), reqd: 1 },
		{ fieldname: "to_date", label: __("To"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "group_by", label: __("Per"), fieldtype: "Select", options: "Truck\nDriver", default: "Truck" },
		{ fieldname: "measure", label: __("Show"), fieldtype: "Select", options: "Trips\nRevenue\nTotal Cost\nNet Income\nFuel (Litres)", default: "Trips" },
		{ fieldname: "vehicle", label: __("Truck"), fieldtype: "Link", options: "Vehicle" },
		{ fieldname: "driver", label: __("Driver"), fieldtype: "Link", options: "Driver" },
	],
};
