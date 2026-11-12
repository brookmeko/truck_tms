// Copyright (c) 2026, Biruk and contributors
// For license information, please see license.txt

const STATUS_COLORS = {
	"Not Invoiced": "var(--red-600)",
	"Draft Invoice": "var(--orange-600)",
	Unpaid: "var(--red-600)",
	"Partly Paid": "var(--orange-600)",
	Paid: "var(--green-600)",
};

frappe.query_reports["Payment Follow-up"] = {
	filters: [
		{ fieldname: "status", label: __("Status"), fieldtype: "Select", options: "\nNot Invoiced\nDraft Invoice\nUnpaid\nPartly Paid\nPaid" },
		{ fieldname: "customer", label: __("Customer"), fieldtype: "Link", options: "Customer" },
		{ fieldname: "include_paid", label: __("Include Paid"), fieldtype: "Check" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;
		if (column.fieldname === "status") {
			return `<b style="color:${STATUS_COLORS[data.status] || "inherit"}">${value}</b>`;
		}
		if (column.fieldname === "days" && data.days > 30 && data.status !== "Paid") {
			return `<b style="color:var(--red-600)">${value}</b>`;
		}
		return value;
	},
};
