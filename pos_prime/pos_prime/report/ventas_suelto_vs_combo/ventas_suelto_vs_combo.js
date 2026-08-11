// Copyright (c) 2026, Ravindu Gajanayaka
// Licensed under GPLv3. See license.txt

frappe.query_reports["Ventas Suelto vs Combo"] = {
	onload(report) {
		report.page.add_inner_message(
			__("Por cada item, cuánto se vendió suelto vs. como parte de un combo, con su cantidad e ingresos totales.")
		);
	},
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
	],
};
