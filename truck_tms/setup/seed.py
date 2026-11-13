"""Seed master data for Truck TMS.

Run with:
    bench --site tms.local execute truck_tms.setup.seed.seed_master_data
Safe to run more than once: existing records are skipped.
"""

import frappe

LOCATIONS = [
	# (location_name, amharic_name, location_type)
	("Djibouti Port", "ጅቡቲ", "Port"),
	("Galafi", "ጋላፊ", "Border"),
	("Dewele", "ደወሌ", "Border"),
	("Semera", "ሰመራ", "Town"),
	("Mile", "ሚሌ", "Town"),
	("Awash", "አዋሽ", "Town"),
	("Metehara", "መተሃራ", "Town"),
	("Dire Dawa", "ድሬ ዳዋ", "City"),
	("Modjo Dry Port", "ሞጆ", "Dry Port"),
	("Kality Customs", "ቃሊቲ", "Customs"),
	("Adama Customs", "አዳማ", "Customs"),
	("Addis Ababa", "አ/አ", "City"),
	("Wolete", "ወለቴ", "Warehouse"),
	("Kadisco", "ካዲስኮ", "Warehouse"),
]

CARGO_TYPES = [
	# (cargo_type_name, amharic_name, is_empty_run)
	("Raw Material", "ጥሬ እቃ", 0),
	("Empty", "በባዶ", 1),
	("Water", "ውሃ", 0),
	("Fertilizer", "ማዳበሪያ", 0),
	("Container", "ኮንቴነር", 0),
	("Steel", "ብረት", 0),
	("Chemical", "ኬሚካል", 0),
	("Castor Seed", "ጉሎ", 0),
]


def seed_master_data():
	created = 0
	for name, amharic, loc_type in LOCATIONS:
		if not frappe.db.exists("Transport Location", name):
			frappe.get_doc(
				{
					"doctype": "Transport Location",
					"location_name": name,
					"amharic_name": amharic,
					"location_type": loc_type,
				}
			).insert()
			created += 1

	for name, amharic, empty in CARGO_TYPES:
		if not frappe.db.exists("Cargo Type", name):
			frappe.get_doc(
				{
					"doctype": "Cargo Type",
					"cargo_type_name": name,
					"amharic_name": amharic,
					"is_empty_run": empty,
				}
			).insert()
			created += 1

	frappe.db.commit()
	print(f"Created {created} records")


EXPENSE_TYPES = [
	# (name, amharic, category, is_fuel)
	("Fuel", "ነዳጅ", "Fuel", 1),
	("Road Toll", "የመንገድ ክፍያ", "Road & Tolls", 0),
	("Weighbridge", "ሚዛን", "Road & Tolls", 0),
	("Parking", "ማቆሚያ", "Road & Tolls", 0),
	("Loading Fee", "የመጫኛ ክፍያ", "Loading & Unloading", 0),
	("Unloading Fee", "የማራገፊያ ክፍያ", "Loading & Unloading", 0),
	("Customs & Documentation", "ጉምሩክና ሰነድ", "Customs & Border", 0),
	("Border Fee", "የድንበር ክፍያ", "Customs & Border", 0),
	("Food & Accommodation", "ምግብና መኝታ", "Food & Accommodation", 0),
	("Truck Repair", "ጥገና", "Maintenance", 0),
	("Tyre", "ጎማ", "Maintenance", 0),
	("Other", "ሌላ", "Other", 0),
]


def ensure_expense_types():
	"""Create the default expense types if they are missing (safe to run many times)."""
	for name, amharic, category, is_fuel in EXPENSE_TYPES:
		if not frappe.db.exists("Trip Expense Type", name):
			frappe.get_doc(
				{
					"doctype": "Trip Expense Type",
					"expense_type_name": name,
					"amharic_name": amharic,
					"category": category,
					"is_fuel": is_fuel,
				}
			).insert(ignore_permissions=True)
