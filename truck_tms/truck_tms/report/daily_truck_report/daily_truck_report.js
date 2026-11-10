// Copyright (c) 2026, Biruk and contributors
// For license information, please see license.txt

frappe.query_reports["Daily Truck Report"] = {
	filters: [],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "stage" && data && !data.trip) {
			// Trucks without a trip (waiting, maintenance) shown in grey
			value = `<span style="color: var(--text-muted)">${value}</span>`;
		}
		return value;
	},
};
