// Copyright (c) 2026, Biruk and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vehicle Driver Assignment", {
	refresh(frm) {
		// Quick button to end an active assignment (keeps history instead of deleting).
		if (!frm.is_new() && frm.doc.is_active) {
			frm.add_custom_button(__("End Assignment"), () => {
				frm.set_value("to_date", frappe.datetime.now_datetime());
				frm.save();
			});
		}
	},
});
