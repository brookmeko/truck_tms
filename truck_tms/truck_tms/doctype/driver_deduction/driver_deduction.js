// Copyright (c) 2026, Biruk and contributors
// For license information, please see license.txt

frappe.ui.form.on("Driver Deduction", {
	refresh(frm) {
		const colors = { Unrecovered: "red", "Partly Recovered": "orange", Recovered: "green" };
		if (frm.doc.docstatus === 1 && colors[frm.doc.status]) {
			frm.page.set_indicator(__(frm.doc.status), colors[frm.doc.status]);
		}
	},
});
