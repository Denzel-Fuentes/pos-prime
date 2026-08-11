// Copyright (c) 2026, Ravindu Gajanayaka
// Licensed under GPLv3. See license.txt

frappe.query_reports["Combos Vendidos"] = {
	onload(report) {
		report.page.add_inner_message(
			__("Cuántas instancias de cada combo se vendieron, y sus ingresos, en el período elegido.")
		);
	},
	filters: [
		{
			fieldname: "period",
			label: __("Period"),
			fieldtype: "Select",
			options: ["Range", "Daily", "Monthly"],
			default: "Range",
		},
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
			fieldname: "combo",
			label: __("Combo"),
			fieldtype: "Link",
			options: "Restaurant Combo",
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
