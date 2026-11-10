// Copyright (c) 2026, Biruk and contributors
// For license information, please see license.txt

frappe.query_reports["Trip Profitability"] = {
	filters: [
		{ fieldname: "from_date", label: __("From"), fieldtype: "Date", default: frappe.datetime.add_months(frappe.datetime.get_today(), -1) },
		{ fieldname: "to_date", label: __("To"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "vehicle", label: __("Truck"), fieldtype: "Link", options: "Vehicle" },
		{ fieldname: "driver", label: __("Driver"), fieldtype: "Link", options: "Driver" },
		{ fieldname: "status", label: __("Status"), fieldtype: "Select", options: "\nPlanned\nIn Progress\nCompleted" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "net_income" && data && data.net_income < 0) {
			value = `<span style="color: var(--red-600)">${value}</span>`;
		}
		return value;
	},
};
