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
