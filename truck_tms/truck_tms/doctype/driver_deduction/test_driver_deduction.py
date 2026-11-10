# Copyright (c) 2026, Biruk and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

# Import the module (not the class) so the Trip tests are not collected and run twice here.
from truck_tms.truck_tms.doctype.trip import test_trip as trip_tests

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = ["Vehicle", "Driver", "Customer", "Company", "Sales Invoice", "Item", "Cost Center", "Trip", "Journal Entry", "Account"]


class IntegrationTestDriverDeduction(IntegrationTestCase):
	"""Reuses the Trip test set-up (truck, driver, assignment, locations)."""

	setUp = trip_tests.IntegrationTestTrip.setUp
	tearDown = trip_tests.IntegrationTestTrip.tearDown
	make_trip = trip_tests.IntegrationTestTrip.make_trip

	def make_deduction(self, amount=10000, installments=2, submit=True):
		frappe.db.delete("Driver Deduction", {"driver": self.driver, "docstatus": 0})
		ded = frappe.get_doc(
			{
				"doctype": "Driver Deduction",
				"driver": self.driver,
				"reason": "Cargo Shortage",
				"amount": amount,
				"installments": installments,
			}
		).insert()
		if submit:
			ded.submit()
		return ded

	def test_installment_amount(self):
		ded = self.make_deduction(10000, 2)
		self.assertEqual(ded.installment_amount, 5000)
		self.assertEqual(ded.status, "Unrecovered")
		self.assertEqual(ded.outstanding_amount, 10000)

	def test_deduction_reduces_driver_refund_and_is_recovered_on_submit(self):
		ded = self.make_deduction(10000, 2)
		trip = self.make_trip()
		trip.append("deductions", {"driver_deduction": ded.name, "amount": 5000})
		trip.save()
		# Without deduction the office owes the driver 3,660; the 5,000 deduction flips it:
		self.assertEqual(trip.deduction_total, 5000)
		self.assertEqual(trip.refund_to_driver, 0)
		self.assertEqual(trip.refund_to_office, 1340)  # 121,660 - 118,000 - 5,000 = -1,340

		trip.submit()
		ded.reload()
		self.assertEqual(ded.recovered_amount, 5000)
		self.assertEqual(ded.outstanding_amount, 5000)
		self.assertEqual(ded.status, "Partly Recovered")

		trip.cancel()
		ded.reload()
		self.assertEqual(ded.outstanding_amount, 10000)
		self.assertEqual(ded.status, "Unrecovered")

	def test_cannot_deduct_more_than_outstanding(self):
		ded = self.make_deduction(10000, 1)
		trip = self.make_trip()
		trip.append("deductions", {"driver_deduction": ded.name, "amount": 12000})
		with self.assertRaises(frappe.ValidationError):
			trip.save()

	def test_draft_deduction_cannot_be_used(self):
		ded = self.make_deduction(10000, 1, submit=False)
		trip = self.make_trip()
		trip.append("deductions", {"driver_deduction": ded.name, "amount": 5000})
		with self.assertRaises(frappe.ValidationError):
			trip.save()

	def test_settlement_entry_with_deduction(self):
		from truck_tms.truck_tms.doctype.trip.accounting import make_settlement_entry

		s = trip_tests.setup_transport_accounts()
		ded = self.make_deduction(10000, 2)
		trip = self.make_trip()
		trip.append("deductions", {"driver_deduction": ded.name, "amount": 5000})
		trip.receipts_verified = 1
		trip.save()
		je = frappe.get_doc("Journal Entry", make_settlement_entry(trip.name))
		credit = {a.account: a.credit for a in je.accounts if a.credit}
		debit = {a.account: a.debit for a in je.accounts if a.debit}
		self.assertEqual(credit[s.deduction_income_account], 5000)
		self.assertEqual(debit[s.bank_account], 1340)  # driver returns 1,340 to the bank
		self.assertEqual(je.total_debit, je.total_credit)
