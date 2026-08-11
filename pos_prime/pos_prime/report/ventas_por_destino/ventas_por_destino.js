// Copyright (c) 2026, Ravindu Gajanayaka
// Licensed under GPLv3. See license.txt

frappe.query_reports["Ventas por Destino"] = {
	onload(report) {
		report.page.add_inner_message(
			__("Órdenes, cantidad e ingresos por día, agrupados por destino (Mesa vs Para llevar).")
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
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
	],
};
