# Copyright (c) 2026, Biruk and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = ["Vehicle", "Driver"]


def make_vehicle(plate):
	if not frappe.db.exists("Vehicle", plate):
		frappe.get_doc(
			{
				"doctype": "Vehicle",
				"license_plate": plate,
				"make": "Test",
				"model": "Test",
				"last_odometer": 0,
				"fuel_type": "Diesel",
				"uom": frappe.db.get_value("UOM", {}, "name"),
			}
		).insert()
	return plate


def make_driver(full_name):
	existing = frappe.db.get_value("Driver", {"full_name": full_name})
	if existing:
		return existing
	return frappe.get_doc({"doctype": "Driver", "full_name": full_name, "status": "Active"}).insert().name


def assign(vehicle, driver, from_date, to_date=None):
	return frappe.get_doc(
		{
			"doctype": "Vehicle Driver Assignment",
			"vehicle": vehicle,
			"driver": driver,
			"from_date": from_date,
			"to_date": to_date,
		}
	).insert()


class IntegrationTestVehicleDriverAssignment(IntegrationTestCase):
	def setUp(self):
		self.truck_a = make_vehicle("TEST-TRUCK-A")
		self.truck_b = make_vehicle("TEST-TRUCK-B")
		self.driver_1 = make_driver("Test Driver One")
		self.driver_2 = make_driver("Test Driver Two")
		# Each test starts clean: remove assignments left by earlier tests.
		frappe.db.delete("Vehicle Driver Assignment", {"vehicle": ("in", [self.truck_a, self.truck_b])})
		frappe.db.delete("Vehicle Driver Assignment", {"driver": ("in", [self.driver_1, self.driver_2])})

	def tearDown(self):
		frappe.db.rollback()

	def test_open_assignment_is_active(self):
		a = assign(self.truck_a, self.driver_1, "2026-01-01 08:00:00")
		self.assertEqual(a.is_active, 1)

	def test_truck_cannot_have_two_drivers(self):
		assign(self.truck_a, self.driver_1, "2026-01-01 08:00:00")
		with self.assertRaises(frappe.ValidationError):
			assign(self.truck_a, self.driver_2, "2026-02-01 08:00:00")

	def test_driver_cannot_drive_two_trucks(self):
		assign(self.truck_a, self.driver_1, "2026-01-01 08:00:00")
		with self.assertRaises(frappe.ValidationError):
			assign(self.truck_b, self.driver_1, "2026-02-01 08:00:00")

	def test_new_driver_after_previous_ended(self):
		assign(self.truck_a, self.driver_1, "2026-01-01 08:00:00", "2026-01-31 18:00:00")
		b = assign(self.truck_a, self.driver_2, "2026-02-01 08:00:00")
		self.assertEqual(b.is_active, 1)

	def test_to_before_from_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			assign(self.truck_a, self.driver_1, "2026-03-01 08:00:00", "2026-02-01 08:00:00")
