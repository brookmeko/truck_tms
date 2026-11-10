# Copyright (c) 2026, Biruk and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from truck_tms.truck_tms.doctype.vehicle_driver_assignment.test_vehicle_driver_assignment import (
	assign,
	make_driver,
	make_vehicle,
)

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = ["Vehicle", "Driver", "Customer", "Company", "Sales Invoice", "Item", "Cost Center"]


def make_location(name, location_type):
	if not frappe.db.exists("Transport Location", name):
		frappe.get_doc(
			{"doctype": "Transport Location", "location_name": name, "location_type": location_type}
		).insert()
	return name


def make_cargo(name, empty=0):
	if not frappe.db.exists("Cargo Type", name):
		frappe.get_doc({"doctype": "Cargo Type", "cargo_type_name": name, "is_empty_run": empty}).insert()
	return name


class IntegrationTestTrip(IntegrationTestCase):
	def setUp(self):
		self.truck = make_vehicle("TEST-TRUCK-T")
		self.driver = make_driver("Test Trip Driver")
		frappe.db.delete("Trip", {"vehicle": self.truck})
		frappe.db.delete("Vehicle Driver Assignment", {"vehicle": self.truck})
		frappe.db.delete("Vehicle Driver Assignment", {"driver": self.driver})
		assign(self.truck, self.driver, "2026-01-01 08:00:00")
		self.addis = make_location("Test Addis", "City")
		self.djibouti = make_location("Test Djibouti", "Port")
		self.empty = make_cargo("Test Empty", empty=1)
		self.raw = make_cargo("Test Raw Material")
		self.company = frappe.db.get_value("Company", {}, "name")

	def tearDown(self):
		frappe.db.rollback()

	def make_trip(self, **extra):
		trip = frappe.get_doc(
			{
				"doctype": "Trip",
				"vehicle": self.truck,
				"company": self.company,
				"start_date": "2026-03-01",
				"loads": [
					{"leg": "Outbound", "origin": self.addis, "destination": self.djibouti, "cargo_type": self.empty},
					{
						"leg": "Return",
						"origin": self.djibouti,
						"destination": self.addis,
						"cargo_type": self.raw,
						"quintals": 400,
						"tariff_per_quintal": 740,
						"demurrage_days": 6,
						"demurrage_rate": 3000,
					},
				],
				# Real row from the April 2016 E.C. settlement sheet (Seid Awel, 3-A17484)
				"fuel_litres": 1000,
				"fuel_cost": 77440,
				"road_expenses": 26220,
				"allowance_base": 15000,
				"extra_days": 6,
				"allowance_per_extra_day": 500,
				"advance_given": 118000,
			}
		)
		trip.update(extra)
		return trip.insert()

	def test_driver_filled_from_assignment(self):
		trip = self.make_trip()
		self.assertEqual(trip.driver, self.driver)

	def test_calculations_match_settlement_sheet(self):
		trip = self.make_trip()
		self.assertEqual(trip.loads[0].revenue, 0)  # empty run
		self.assertEqual(trip.loads[1].revenue, 314000)  # 400 x 740 + 6 x 3000
		self.assertEqual(trip.allowance, 18000)  # 15000 + 6 x 500
		self.assertEqual(trip.total_cost, 121660)  # 77440 + 26220 + 18000
		self.assertEqual(trip.refund_to_driver, 3660)  # 121660 - 118000
		self.assertEqual(trip.refund_to_office, 0)
		self.assertEqual(trip.net_income, 192340)  # 314000 - 121660

	def test_internal_job_has_no_revenue(self):
		trip = self.make_trip()
		trip.loads[1].is_internal_job = 1
		trip.save()
		self.assertEqual(trip.total_revenue, 0)

	def test_truck_cannot_be_on_two_active_trips(self):
		self.make_trip()
		with self.assertRaises(frappe.ValidationError):
			self.make_trip()

	def test_current_stage(self):
		trip = self.make_trip()
		self.assertEqual(trip.current_stage, "Assigned (Outbound)")
		trip.loads[0].stage = "Delivered"
		trip.loads[1].stage = "At Customs"
		trip.save()
		self.assertEqual(trip.current_stage, "At Customs (Return)")

	def test_stage_change_is_logged_with_location(self):
		trip = self.make_trip()
		trip.current_location = self.djibouti
		trip.loads[0].stage = "Delivered"
		trip.loads[1].stage = "Loading"
		trip.save()
		logs = frappe.get_all(
			"Trip Stage Log", filters={"trip": trip.name}, fields=["leg", "from_stage", "to_stage", "location"]
		)
		self.assertEqual(len(logs), 2)
		loading = next(log for log in logs if log.leg == "Return")
		self.assertEqual(loading.from_stage, "Assigned")
		self.assertEqual(loading.to_stage, "Loading")
		self.assertEqual(loading.location, self.djibouti)

	def test_stage_sets_dates_automatically(self):
		trip = self.make_trip()
		trip.loads[1].stage = "At Customs"
		trip.save()
		self.assertTrue(trip.loads[1].customs_in_date)
		trip.loads[1].stage = "Unloading"
		trip.save()
		self.assertTrue(trip.loads[1].customs_out_date)
		self.assertTrue(trip.loads[1].unloading_date)

	def test_daily_truck_report_shows_active_load(self):
		from truck_tms.truck_tms.report.daily_truck_report.daily_truck_report import execute

		trip = self.make_trip()
		trip.loads[0].stage = "Delivered"
		trip.loads[1].stage = "Border Crossing"
		trip.save()
		columns, rows = execute({})
		row = next(r for r in rows if r["vehicle"] == self.truck)
		self.assertEqual(row["trip"], trip.name)
		self.assertEqual(row["stage"], "Border Crossing (Return)")
		self.assertEqual(row["quintals"], 400)

	def test_truck_gets_cost_center(self):
		cc = frappe.db.get_value("Vehicle", self.truck, "cost_center")
		if not cc:  # vehicle may pre-date the hook
			from truck_tms.setup.vehicle import create_cost_center

			create_cost_center(frappe.get_doc("Vehicle", self.truck))
			cc = frappe.db.get_value("Vehicle", self.truck, "cost_center")
		self.assertTrue(cc and cc.startswith(self.truck))

	def test_create_invoice_for_paying_load_only(self):
		from truck_tms.truck_tms.doctype.trip.invoicing import make_sales_invoices

		customer = make_customer("Test Freight Customer")
		trip = self.make_trip()
		trip.loads[1].customer = customer
		trip.loads[1].shortage_amount = 10000
		trip.save()

		invoices = make_sales_invoices(trip.name)
		self.assertEqual(len(invoices), 1)  # empty outbound leg is not invoiced
		si = frappe.get_doc("Sales Invoice", invoices[0])
		self.assertEqual(si.trip, trip.name)
		self.assertEqual(si.docstatus, 0)  # draft for finance review
		self.assertEqual(si.total, 314000)  # 400 x 740 + 6 x 3000
		self.assertEqual(si.grand_total, 304000)  # minus 10,000 shortage
		self.assertEqual(frappe.db.get_value("Trip Load", trip.loads[1].name, "sales_invoice"), si.name)

		# Running again does not create duplicates
		self.assertEqual(make_sales_invoices(trip.name), [])


def make_customer(name):
	if not frappe.db.exists("Customer", name):
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": name,
				"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name"),
				"territory": frappe.db.get_value("Territory", {"is_group": 0}, "name"),
			}
		).insert()
	return name
