// Copyright (c) 2026, Biruk and contributors
// For license information, please see license.txt

frappe.ui.form.on("Trip", {
	setup(frm) {
		frm.set_query("vehicle", () => ({ filters: { truck_status: ["!=", "Inactive"] } }));
	},

	onload(frm) {
		if (frm.is_new() && !frm.doc.company) {
			frm.set_value("company", frappe.defaults.get_user_default("Company"));
		}
	},

	vehicle(frm) {
		if (!frm.doc.vehicle) return;
		frappe.call({
			method: "truck_tms.truck_tms.doctype.trip.trip.get_vehicle_driver",
			args: { vehicle: frm.doc.vehicle },
			callback(r) {
				if (r.message) {
					frm.set_value("driver", r.message);
				} else {
					frappe.msgprint(__("This truck has no active driver assignment."));
				}
			},
		});
	},

	refresh(frm) {
		if (!frm.is_new() && frm.doc.docstatus < 2) {
			frm.add_custom_button(
				__("Create Invoices"),
				() => {
					frappe.call({
						method: "truck_tms.truck_tms.doctype.trip.invoicing.make_sales_invoices",
						args: { trip: frm.doc.name },
						freeze: true,
						callback(r) {
							if (r.message && r.message.length) {
								frappe.msgprint(__("Created draft invoices: {0}", [r.message.join(", ")]));
								frm.reload_doc();
							}
						},
					});
				},
				__("Billing")
			);
		}
		if (!frm.is_new() && frm.doc.docstatus < 2) {
			const call = (method, label) =>
				frappe.call({
					method: `truck_tms.truck_tms.doctype.trip.accounting.${method}`,
					args: { trip: frm.doc.name },
					freeze: true,
					callback(r) {
						if (r.message) {
							const names = Array.isArray(r.message) ? r.message.join(", ") : r.message;
							frappe.msgprint(__("{0} created as draft: {1}", [label, names]));
							frm.reload_doc();
						}
					},
				});
			if ((frm.doc.advances || []).some((row) => !row.journal_entry)) {
				frm.add_custom_button(__("Record Advances Paid"), () => call("make_advance_entries", __("Advance entries")), __("Settlement"));
			}
			if (!frm.doc.settlement_journal_entry && frm.doc.receipts_verified) {
				frm.add_custom_button(__("Create Settlement Entry"), () => call("make_settlement_entry", __("Settlement entry")), __("Settlement"));
			}
		}
		if (frm.doc.docstatus === 0 && frm.doc.driver) {
			frm.add_custom_button(
				__("Get Driver Deductions"),
				() => {
					frappe.call({
						method: "truck_tms.truck_tms.doctype.driver_deduction.driver_deduction.get_outstanding_deductions",
						args: {
							driver: frm.doc.driver,
							exclude: (frm.doc.deductions || []).map((d) => d.driver_deduction),
						},
						callback(r) {
							if (!r.message || !r.message.length) {
								frappe.msgprint(__("No outstanding deductions for this driver."));
								return;
							}
							r.message.forEach((d) => {
								const row = frm.add_child("deductions");
								row.driver_deduction = d.name;
								row.reason = d.reason;
								row.amount = d.suggested;
							});
							frm.refresh_field("deductions");
							frm.dirty();
						},
					});
				},
				__("Settlement")
			);
		}
		if (frm.doc.docstatus === 0 && !frm.is_new() && frm.doc.status === "Planned") {
			frm.add_custom_button(__("Start Trip"), () => {
				frm.set_value("status", "In Progress");
				frm.save();
			});
		}
	},
});

frappe.ui.form.on("Trip Advance", {
	amount(frm) {
		frm.set_value("advance_given", (frm.doc.advances || []).reduce((t, r) => t + (r.amount || 0), 0));
	},
	advances_remove(frm) {
		frm.set_value("advance_given", (frm.doc.advances || []).reduce((t, r) => t + (r.amount || 0), 0));
	},
});

// Driver expense form: show running totals while lines are typed in (the server recalculates on save).
function update_expense_totals(frm) {
	let fuel = 0, litres = 0, other = 0, rejected = 0;
	(frm.doc.expenses || []).forEach((r) => {
		if (r.rejected) {
			rejected += r.amount || 0;
		} else if (r.is_fuel) {
			fuel += r.amount || 0;
			litres += r.litres || 0;
		} else {
			other += r.amount || 0;
		}
	});
	frm.set_value({ fuel_cost: fuel, fuel_litres: litres, road_expenses: other, rejected_expenses: rejected });
}

frappe.ui.form.on("Trip Expense", {
	amount: update_expense_totals,
	litres: update_expense_totals,
	rejected: update_expense_totals,
	is_fuel: update_expense_totals,
	expenses_remove: update_expense_totals,
	expenses_add(frm, cdt, cdn) {
		// New line defaults to the trip's last expense date
		const rows = frm.doc.expenses || [];
		const prev = rows.length > 1 ? rows[rows.length - 2].date : frm.doc.start_date;
		if (prev) frappe.model.set_value(cdt, cdn, "date", prev);
	},
});
