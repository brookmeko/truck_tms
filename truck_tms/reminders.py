"""Daily reminders (bell notification + email), sent every morning by the scheduler.

Finance / managers get: loads not invoiced, draft invoices, unpaid invoices over 30 days,
trips delivered but not settled with the driver.
Dispatchers / managers get: active trips not updated for 2 days.
"""

import frappe
from frappe import _
from frappe.utils import add_days, flt, fmt_money, get_url_to_report, now_datetime, today

FINANCE_ROLES = ("Transport Finance", "Transport Manager")
OPERATIONS_ROLES = ("Transport Dispatcher", "Transport Manager")
OVERDUE_DAYS = 30
STALE_DAYS = 2


def get_reminder_summary():
	from truck_tms.truck_tms.report.payment_follow_up.payment_follow_up import get_data

	follow_up = get_data(frappe._dict())
	not_invoiced = [r for r in follow_up if r["status"] == "Not Invoiced"]
	drafts = [r for r in follow_up if r["status"] == "Draft Invoice"]
	overdue = [r for r in follow_up if r["status"] in ("Unpaid", "Partly Paid") and r["days"] > OVERDUE_DAYS]

	unsettled = frappe.db.sql(
		"""select count(*) from `tabTrip`
		where docstatus < 2 and board_column = 'Settlement' and coalesce(settlement_journal_entry, '') = ''"""
	)[0][0]
	stale = frappe.get_all(
		"Trip",
		filters={
			"docstatus": 0,
			"status": ("in", ("Planned", "In Progress")),
			"modified": ("<", add_days(now_datetime(), -STALE_DAYS)),
		},
		pluck="name",
	)
	return frappe._dict(
		not_invoiced=len(not_invoiced),
		drafts=len(drafts),
		overdue=len(overdue),
		overdue_amount=sum(flt(r["outstanding"]) for r in overdue),
		unsettled=unsettled,
		stale=stale,
	)


def send_daily_reminders():
	s = get_reminder_summary()
	follow_up_url = get_url_to_report("Payment Follow-up", "Script Report", "Trip")

	finance_lines = []
	if s.not_invoiced:
		finance_lines.append(_("{0} delivered load(s) not invoiced yet").format(s.not_invoiced))
	if s.drafts:
		finance_lines.append(_("{0} draft invoice(s) waiting to be submitted").format(s.drafts))
	if s.overdue:
		finance_lines.append(
			_("{0} invoice(s) unpaid for more than {1} days ({2})").format(
				s.overdue, OVERDUE_DAYS, fmt_money(s.overdue_amount, currency="ETB")
			)
		)
	if s.unsettled:
		finance_lines.append(_("{0} delivered trip(s) not settled with the driver").format(s.unsettled))
	if finance_lines:
		notify(FINANCE_ROLES, _("Payment follow-up: {0} item(s) need attention").format(len(finance_lines)),
			finance_lines, follow_up_url)

	if s.stale:
		notify(
			OPERATIONS_ROLES,
			_("{0} active trip(s) not updated for {1} days").format(len(s.stale), STALE_DAYS),
			[_("Call the drivers and update: {0}").format(", ".join(s.stale[:10]))],
			"/desk/trip/view/kanban/Operations Board",
		)
	return s


def notify(roles, subject, lines, link):
	users = get_users_with_roles(roles)
	if not users:
		return
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	ensure_alert_type()
	body = "<ul>" + "".join(f"<li>{frappe.utils.escape_html(line)}</li>" for line in lines) + "</ul>"
	enqueue_create_notification(
		users,
		{"type": "Alert", "subject": subject, "email_content": body, "link": link},
	)


def get_users_with_roles(roles):
	users = frappe.get_all(
		"Has Role", filters={"role": ("in", roles), "parenttype": "User"}, pluck="parent", distinct=True
	)
	return frappe.get_all("User", filters={"name": ("in", users or [""]), "enabled": 1}, pluck="name")


def ensure_alert_type():
	if frappe.db.exists("DocType", "Notification Type") and not frappe.db.exists("Notification Type", "Alert"):
		frappe.get_doc({"doctype": "Notification Type", "type_name": "Alert", "enabled": 1}).insert(
			ignore_permissions=True
		)


# ----- Custom number cards ---------------------------------------------------


@frappe.whitelist()
def card_loads_not_invoiced(filters=None):
	return get_reminder_summary().not_invoiced


@frappe.whitelist()
def card_unpaid_over_30_days(filters=None):
	return {"value": get_reminder_summary().overdue_amount, "fieldtype": "Currency"}
