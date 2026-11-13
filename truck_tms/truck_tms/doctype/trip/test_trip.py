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
IGNORE_TEST_RECORD_DEPENDENCIES = ["Vehicle", "Driver", "Customer", "Company", "Sales Invoice", "Item", "Cost Center", "Journal Entry", "Account", "Trip Expense Type", "User"]


def make_location(name, location_type):
	if not frappe.db.exists("Transport Location", name):
		frappe.get_doc(
			{"doctype": "Transport Location", "location_name": name, "location_type": location_type}
		).insert()
	return name


def make_expense_type(name, is_fuel=0, expense_account=None):
	if not frappe.db.exists("Trip Expense Type", name):
		frappe.get_doc(
			{"doctype": "Trip Expense Type", "expense_type_name": name, "category": "Fuel" if is_fuel else "Other", "is_fuel": is_fuel}
		).insert()
	frappe.db.set_value("Trip Expense Type", name, "expense_account", expense_account)
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
		self.fuel_type = make_expense_type("Test Fuel", is_fuel=1)
		self.toll_type = make_expense_type("Test Road Toll")
		self.loading_type = make_expense_type("Test Loading Fee")

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
				# The driver's expense form: fuel 77,440 (1,000 L) + other expenses 26,220
				"expenses": [
					{"date": "2026-03-01", "expense_type": self.fuel_type, "litres": 600, "amount": 46464, "receipt_no": "F-1"},
					{"date": "2026-03-04", "expense_type": self.fuel_type, "litres": 400, "amount": 30976, "receipt_no": "F-2"},
					{"date": "2026-03-02", "expense_type": self.toll_type, "amount": 20000, "receipt_no": "T-1"},
					{"date": "2026-03-05", "expense_type": self.loading_type, "amount": 6220, "receipt_no": "L-1"},
				],
				"allowance_base": 15000,
				"extra_days": 6,
				"allowance_per_extra_day": 500,
				# Three advances, as in the sheet formula =80000+35000+3000
				"advances": [
					{"date": "2026-03-01", "amount": 80000, "purpose": "Fuel"},
					{"date": "2026-03-03", "amount": 35000, "purpose": "Road Expenses"},
					{"date": "2026-03-05", "amount": 3000, "purpose": "Mixed"},
				],
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

	def test_expense_form_totals(self):
		trip = self.make_trip()
		self.assertEqual(trip.fuel_cost, 77440)
		self.assertEqual(trip.fuel_litres, 1000)
		self.assertEqual(trip.road_expenses, 26220)
		self.assertEqual(trip.rejected_expenses, 0)

	def test_rejected_expense_is_not_paid(self):
		trip = self.make_trip()
		trip.expenses[3].rejected = 1  # no valid receipt for the 6,220 loading fee
		trip.save()
		self.assertEqual(trip.road_expenses, 20000)
		self.assertEqual(trip.rejected_expenses, 6220)
		self.assertEqual(trip.total_cost, 115440)  # 77440 + 20000 + 18000
		self.assertEqual(trip.refund_to_driver, 0)
		self.assertEqual(trip.refund_to_office, 2560)  # 118000 - 115440: driver returns money

	def test_expense_amount_must_be_positive(self):
		trip = self.make_trip()
		trip.expenses[0].amount = 0
		with self.assertRaises(frappe.ValidationError):
			trip.save()

	def make_user(self, email, role):
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": role, "send_welcome_email": 0, "roles": [{"role": role}]}
			).insert(ignore_permissions=True)
		return email

	def test_dispatcher_enters_expenses_but_cannot_check_receipts(self):
		dispatcher = self.make_user("test-dispatcher@truck-tms.test", "Transport Dispatcher")
		accountant = self.make_user("test-accountant@truck-tms.test", "Transport Finance")
		trip = self.make_trip()
		try:
			# Dispatcher adds a line and tries to tick finance-only boxes: they are ignored
			frappe.set_user(dispatcher)
			trip = frappe.get_doc("Trip", trip.name)
			trip.append("expenses", {"date": "2026-03-06", "expense_type": self.toll_type, "amount": 1000})
			trip.expenses[0].rejected = 1
			trip.receipts_verified = 1
			trip.save()
			self.assertEqual(trip.road_expenses, 27220)  # new line counted
			self.assertEqual(trip.rejected_expenses, 0)
			self.assertFalse(frappe.db.get_value("Trip", trip.name, "receipts_verified"))

			# Accountant rejects a line and checks the receipts
			frappe.set_user(accountant)
			trip = frappe.get_doc("Trip", trip.name)
			trip.expenses[4].rejected = 1
			trip.receipts_verified = 1
			trip.save()
			self.assertEqual(trip.rejected_expenses, 1000)
			self.assertEqual(trip.receipts_verified_by, accountant)

			# Now the dispatcher cannot change the lines any more
			frappe.set_user(dispatcher)
			trip = frappe.get_doc("Trip", trip.name)
			trip.expenses[0].amount = 50000
			with self.assertRaises(frappe.ValidationError):
				trip.save()
		finally:
			frappe.set_user("Administrator")

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

	def test_advance_and_settlement_entries(self):
		from truck_tms.truck_tms.doctype.trip.accounting import make_advance_entries, make_settlement_entry

		s = setup_transport_accounts()
		trip = self.make_trip()
		self.assertEqual(trip.advance_given, 118000)  # 80,000 + 35,000 + 3,000

		entries = make_advance_entries(trip.name)
		self.assertEqual(len(entries), 3)  # one bank entry per advance
		first = frappe.get_doc("Journal Entry", entries[0])
		self.assertEqual(first.docstatus, 0)  # draft for the accountant
		lines = {(a.account, a.debit, a.credit) for a in first.accounts}
		self.assertEqual(lines, {(s.driver_advance_account, 80000, 0), (s.bank_account, 0, 80000)})
		with self.assertRaises(frappe.ValidationError):
			make_advance_entries(trip.name)  # nothing left to record

		# A posted advance cannot be changed
		trip.reload()
		trip.advances[0].amount = 90000
		with self.assertRaises(frappe.ValidationError):
			trip.save()
		trip.reload()

		# Settlement is blocked until receipts are checked
		with self.assertRaises(frappe.ValidationError):
			make_settlement_entry(trip.name)
		trip.reload()
		trip.receipts_verified = 1
		trip.save()
		self.assertEqual(trip.receipts_verified_by, frappe.session.user)

		# Loading fees go to their own account (set on the expense type)
		from truck_tms.setup.accounts import get_or_create_account

		loading_account = get_or_create_account(trip.company, "Test Loading Expense", "Expense", "", "Direct Expenses")
		make_expense_type(self.loading_type, expense_account=loading_account)

		je = frappe.get_doc("Journal Entry", make_settlement_entry(trip.name))
		debit = {a.account: a.debit for a in je.accounts if a.debit}
		credit = {a.account: a.credit for a in je.accounts if a.credit}
		self.assertEqual(debit[s.fuel_expense_account], 77440)
		self.assertEqual(debit[s.road_expense_account], 20000)
		self.assertEqual(debit[loading_account], 6220)
		self.assertEqual(debit[s.allowance_expense_account], 18000)
		self.assertEqual(credit[s.driver_advance_account], 118000)  # advance cleared
		self.assertEqual(credit[s.bank_account], 3660)  # bank refunds the driver
		self.assertEqual(je.total_debit, je.total_credit)


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


def setup_transport_accounts():
	"""Default accounts + a test bank account in Transport Settings."""
	from truck_tms.setup.accounts import ensure_transport_accounts, get_or_create_account

	ensure_transport_accounts()
	settings = frappe.get_single("Transport Settings")
	if not settings.bank_account:
		company = frappe.db.get_value("Company", {}, "name")
		settings.bank_account = get_or_create_account(company, "Test Bank", "Asset", "Bank", "Bank Accounts")
		settings.save()
	return settings


class IntegrationTestReports(IntegrationTestCase):
	"""The three management reports, using the Trip test set-up."""

	setUp = IntegrationTestTrip.setUp
	tearDown = IntegrationTestTrip.tearDown
	make_trip = IntegrationTestTrip.make_trip

	def test_trip_profitability(self):
		from truck_tms.truck_tms.report.trip_profitability.trip_profitability import execute

		trip = self.make_trip()
		columns, rows = execute({"vehicle": self.truck})
		row = next(r for r in rows if r.name == trip.name)
		self.assertEqual(row.net_income, 192340)
		self.assertIn("Test Djibouti → Test Addis", row.route)
		self.assertAlmostEqual(row.margin, 192340 / 314000 * 100, places=2)

	def test_truck_profit_by_month(self):
		from truck_tms.truck_tms.report.truck_profit_by_month.truck_profit_by_month import execute

		self.make_trip()
		columns, rows, message, chart = execute({"vehicle": self.truck})
		self.assertEqual(rows[0].month, "2026-03")
		self.assertEqual(rows[0].trips, 1)
		self.assertEqual(rows[0].net, 192340)
		self.assertEqual(chart["data"]["labels"], [self.truck])

	def test_driver_settlement_summary(self):
		from truck_tms.truck_tms.report.driver_settlement_summary.driver_settlement_summary import execute

		self.make_trip()
		columns, rows = execute({"driver": self.driver})
		self.assertEqual(rows[0].refund_to_driver, 3660)
		self.assertEqual(rows[0].unsettled, 1)


class IntegrationTestBoardAPI(IntegrationTestCase):
	"""API used by the frontend board."""

	setUp = IntegrationTestTrip.setUp
	tearDown = IntegrationTestTrip.tearDown
	make_trip = IntegrationTestTrip.make_trip

	def test_board_places_trip_in_column_of_active_load(self):
		from truck_tms.api import get_board

		trip = self.make_trip()
		trip.loads[0].stage = "Delivered"
		trip.loads[1].stage = "At Customs"
		trip.save()
		card = next(c for c in get_board()["cards"] if c["name"] == trip.name)
		self.assertEqual(card["column"], "customs")
		self.assertEqual(card["stage"], "At Customs")

	def test_set_load_stage_moves_trip_and_logs(self):
		from truck_tms.api import set_load_stage

		trip = self.make_trip()
		result = set_load_stage(trip.name, trip.loads[0].name, "In Transit", self.djibouti)
		trip.reload()
		self.assertEqual(trip.status, "In Progress")
		self.assertEqual(trip.current_location, self.djibouti)
		self.assertEqual(result["current_stage"], "In Transit (Outbound)")
		self.assertTrue(frappe.db.exists("Trip Stage Log", {"trip": trip.name, "to_stage": "In Transit"}))

	def test_set_load_stage_rejects_unknown_stage(self):
		from truck_tms.api import set_load_stage

		trip = self.make_trip()
		with self.assertRaises(frappe.ValidationError):
			set_load_stage(trip.name, trip.loads[0].name, "Flying")

	def test_dashboard_numbers(self):
		from truck_tms.api import get_dashboard

		self.make_trip()
		data = get_dashboard()
		self.assertGreaterEqual(data["active_trips"], 1)
		self.assertIn("trucks_by_status", data)


class IntegrationTestOperationsBoard(IntegrationTestCase):
	"""Kanban board column on the Trip."""

	setUp = IntegrationTestTrip.setUp
	tearDown = IntegrationTestTrip.tearDown
	make_trip = IntegrationTestTrip.make_trip

	def test_board_column_follows_active_load(self):
		trip = self.make_trip()
		self.assertEqual(trip.board_column, "Assigned")
		trip.loads[0].stage = "Delivered"
		trip.loads[1].stage = "At Customs"
		trip.save()
		self.assertEqual(trip.board_column, "Border & Customs")
		trip.loads[1].stage = "Delivered"
		trip.save()
		self.assertEqual(trip.board_column, "Settlement")

	def test_dragging_card_moves_active_load(self):
		trip = self.make_trip()
		# What the Kanban view does when a card is dragged to "In Transit"
		trip.board_column = "In Transit"
		trip.save()
		self.assertEqual(trip.loads[0].stage, "In Transit")
		self.assertEqual(trip.board_column, "In Transit")
		self.assertEqual(trip.current_stage, "In Transit (Outbound)")


class IntegrationTestDriverAndMonthlyReports(IntegrationTestCase):
	setUp = IntegrationTestTrip.setUp
	tearDown = IntegrationTestTrip.tearDown
	make_trip = IntegrationTestTrip.make_trip

	def test_driver_expense_report_per_trip_and_per_driver(self):
		from truck_tms.truck_tms.report.driver_expense_report.driver_expense_report import execute

		trip = self.make_trip()
		f = {"from_date": "2026-01-01", "to_date": "2026-12-31", "driver": self.driver}
		_cols, rows = execute({**f, "group_by": "Trip"})
		row = next(r for r in rows if r.trip == trip.name)
		self.assertEqual(row.total_cost, 121660)
		self.assertEqual(row.fuel_litres, 1000)
		_cols, rows = execute({**f, "group_by": "Driver"})
		self.assertEqual(rows[0].trips, 1)
		self.assertEqual(rows[0].allowance, 18000)

	def test_monthly_performance_trips_per_truck(self):
		from truck_tms.truck_tms.report.monthly_performance.monthly_performance import execute

		self.make_trip()  # starts 2026-03-01
		cols, rows, _msg, chart = execute(
			{"from_date": "2026-01-01", "to_date": "2026-06-30", "group_by": "Truck", "measure": "Trips", "vehicle": self.truck}
		)
		self.assertEqual([c["label"] for c in cols][1:7], ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"])
		self.assertEqual(rows[0]["2026_03"], 1)
		self.assertEqual(rows[0]["total"], 1)
		cols, rows, _msg, chart = execute(
			{"from_date": "2026-01-01", "to_date": "2026-06-30", "group_by": "Driver", "measure": "Net Income", "driver": self.driver}
		)
		self.assertEqual(rows[0]["2026_03"], 192340)


class IntegrationTestPaymentFollowUp(IntegrationTestCase):
	setUp = IntegrationTestTrip.setUp
	tearDown = IntegrationTestTrip.tearDown
	make_trip = IntegrationTestTrip.make_trip

	def delivered_trip(self):
		trip = self.make_trip()
		trip.loads[1].customer = make_customer("Test Freight Customer")
		trip.loads[0].stage = "Delivered"
		trip.loads[1].stage = "Delivered"
		trip.save()
		return trip

	def test_follow_up_statuses(self):
		from truck_tms.truck_tms.doctype.trip.invoicing import make_sales_invoices
		from truck_tms.truck_tms.report.payment_follow_up.payment_follow_up import execute

		trip = self.delivered_trip()
		row = lambda: next(r for r in execute({})[1] if r["trip"] == trip.name)
		self.assertEqual(row()["status"], "Not Invoiced")
		self.assertEqual(row()["amount"], 314000)

		si = frappe.get_doc("Sales Invoice", make_sales_invoices(trip.name)[0])
		self.assertEqual(row()["status"], "Draft Invoice")

		si.submit()
		self.assertEqual(row()["status"], "Unpaid")
		self.assertEqual(row()["outstanding"], 314000)

	def test_reminders_notify_finance(self):
		from truck_tms.reminders import send_daily_reminders

		self.delivered_trip()
		user = "finance.reminder@test.local"
		if not frappe.db.exists("User", user):
			frappe.get_doc({"doctype": "User", "email": user, "first_name": "Finance", "send_welcome_email": 0,
				"roles": [{"role": "Transport Finance"}]}).insert(ignore_permissions=True)
		summary = send_daily_reminders()
		self.assertGreaterEqual(summary.not_invoiced, 1)
		self.assertTrue(frappe.db.exists("Notification Log", {"for_user": user}))
